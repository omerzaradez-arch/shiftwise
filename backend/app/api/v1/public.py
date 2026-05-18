"""Public endpoints — no authentication required."""
import math
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.models import Employee, ScheduleWeek, ScheduledShift, Organization
from app.models.attendance import Attendance
from app.api.v1.auth import verify_checkin_token

router = APIRouter()


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class CheckinRequest(BaseModel):
    token: str
    lat: float
    lng: float


@router.get("/checkin/{token}")
async def get_checkin_info(token: str, db: AsyncSession = Depends(get_db)):
    """Used by the web page to display shift details before requesting GPS."""
    payload = verify_checkin_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="טוקן לא תקף או פג תוקף")
    shift = await db.get(ScheduledShift, payload["sid"])
    emp = await db.get(Employee, payload["eid"])
    if not shift or not emp:
        raise HTTPException(status_code=404, detail="משמרת לא נמצאה")
    return {
        "employee_name": emp.name,
        "shift_date": shift.date.isoformat(),
        "start_time": shift.start_time.strftime("%H:%M"),
        "end_time": shift.end_time.strftime("%H:%M"),
    }


@router.post("/checkin")
async def submit_checkin(req: CheckinRequest, db: AsyncSession = Depends(get_db)):
    """Receive GPS from the check-in web page and register attendance."""
    payload = verify_checkin_token(req.token)
    if not payload:
        raise HTTPException(status_code=401, detail="טוקן לא תקף או פג תוקף")

    shift = await db.get(ScheduledShift, payload["sid"])
    emp = await db.get(Employee, payload["eid"])
    if not shift or not emp:
        raise HTTPException(status_code=404, detail="משמרת לא נמצאה")

    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    existing = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == emp.id,
                Attendance.date == today,
                Attendance.check_out == None,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="כבר רשומה כניסה פתוחה להיום")

    # Validate location vs org settings
    org = await db.get(Organization, emp.org_id)
    is_valid = True
    dist = None
    if org and org.settings:
        s = org.settings
        biz_lat = s.get("location_lat")
        biz_lng = s.get("location_lng")
        radius = float(s.get("location_radius", 200))
        if biz_lat and biz_lng:
            dist = _haversine(req.lat, req.lng, float(biz_lat), float(biz_lng))
            is_valid = dist <= radius

    if not is_valid:
        return {
            "ok": False,
            "distance_m": int(dist) if dist is not None else None,
            "message": f"לא נמצאת בכתובת המשמרת — מרחק {int(dist) if dist is not None else '?'} מ׳",
        }

    now_utc = datetime.now(timezone.utc)
    att = Attendance(
        id=str(uuid.uuid4()),
        employee_id=emp.id,
        org_id=emp.org_id,
        date=today,
        check_in=now_utc,
        check_in_lat=req.lat,
        check_in_lng=req.lng,
        is_valid_location=True,
    )
    db.add(att)
    await db.commit()

    return {
        "ok": True,
        "distance_m": int(dist) if dist is not None else None,
        "check_in_time": (now_utc + timedelta(hours=3)).strftime("%H:%M"),
        "employee_name": emp.name,
    }

DAY_NAMES = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]


@router.get("/schedule/{org_id}")
async def public_schedule(org_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the current published weekly schedule for an org. No auth required."""

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="לא נמצא")

    # Find the most recent published schedule
    result = await db.execute(
        select(ScheduleWeek)
        .where(
            ScheduleWeek.org_id == org_id,
            ScheduleWeek.status == "published",
        )
        .order_by(ScheduleWeek.week_start.desc())
        .limit(1)
    )
    week = result.scalar_one_or_none()

    if not week:
        return {"org_name": org.name, "week": None, "days": []}

    # Load all shifts for the week
    shifts_result = await db.execute(
        select(ScheduledShift)
        .where(
            ScheduledShift.week_id == week.id,
            ScheduledShift.status != "cancelled",
        )
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
    )
    shifts = shifts_result.scalars().all()

    # Load all employees
    emp_ids = list({s.employee_id for s in shifts})
    emps_result = await db.execute(
        select(Employee).where(Employee.id.in_(emp_ids))
    )
    emp_map = {e.id: e.name for e in emps_result.scalars().all()}

    # Group by day
    days_map: dict = {}
    for shift in shifts:
        d = shift.date.isoformat()
        dow = (shift.date.weekday() + 1) % 7
        shift_type = "morning" if shift.start_time.hour < 12 else "evening"
        if d not in days_map:
            days_map[d] = {
                "date": d,
                "day_name": DAY_NAMES[dow],
                "morning": [],
                "evening": [],
            }
        days_map[d][shift_type].append({
            "name": emp_map.get(shift.employee_id, "?"),
            "start": shift.start_time.strftime("%H:%M"),
            "end": shift.end_time.strftime("%H:%M"),
        })

    # Sort days
    days = sorted(days_map.values(), key=lambda d: d["date"])

    return {
        "org_name": org.name,
        "week_start": week.week_start.isoformat(),
        "week_end": (week.week_start + timedelta(days=6)).isoformat(),
        "days": days,
    }
