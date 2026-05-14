from datetime import datetime, date, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from app.database import get_db
from app.models import Employee, Attendance, Organization
from app.api.v1.auth import get_current_user

router = APIRouter()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def haversine_distance(lat1, lng1, lat2, lng2) -> float:
    """Returns distance in meters between two GPS coordinates."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def get_org_location(org: Organization):
    """Returns (lat, lng, radius_meters) from org settings, or None if not set."""
    s = org.settings or {}
    lat = s.get("location_lat")
    lng = s.get("location_lng")
    radius = s.get("location_radius", 200)
    if lat is not None and lng is not None:
        return float(lat), float(lng), float(radius)
    return None


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class CheckInRequest(BaseModel):
    lat: float | None = None
    lng: float | None = None


class CheckOutRequest(BaseModel):
    lat: float | None = None
    lng: float | None = None


class AttendanceOut(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    date: str
    check_in: str
    check_out: str | None
    total_minutes: int | None
    is_valid_location: bool
    hourly_rate: float | None
    total_pay: float | None


# ──────────────────────────────────────────────
# Employee endpoints
# ──────────────────────────────────────────────

@router.post("/checkin")
async def check_in(
    body: CheckInRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()

    # Check if already checked in today
    existing = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == current_user.id,
                Attendance.date == today,
                Attendance.check_out == None,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="כבר רשום כניסה היום")

    # Validate location
    org = await db.get(Organization, current_user.org_id)
    is_valid = True
    if body.lat is not None and body.lng is not None:
        loc = get_org_location(org)
        if loc:
            dist = haversine_distance(body.lat, body.lng, loc[0], loc[1])
            is_valid = dist <= loc[2]
    else:
        # No GPS provided — still allow but mark as not validated
        is_valid = True

    attendance = Attendance(
        employee_id=current_user.id,
        org_id=current_user.org_id,
        date=today,
        check_in=datetime.now(timezone.utc),
        check_in_lat=body.lat,
        check_in_lng=body.lng,
        is_valid_location=is_valid,
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)

    return {
        "ok": True,
        "attendance_id": attendance.id,
        "check_in": attendance.check_in.isoformat(),
        "is_valid_location": is_valid,
        "message": "כניסה נרשמה בהצלחה ✅" if is_valid else "כניסה נרשמה — המיקום לא אומת ⚠️",
    }


@router.post("/checkout")
async def check_out(
    body: CheckOutRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == current_user.id,
                Attendance.date == today,
                Attendance.check_out == None,
            )
        )
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=400, detail="לא נמצאת רשומת כניסה פתוחה")

    now = datetime.now(timezone.utc)
    total_minutes = int((now - attendance.check_in).total_seconds() / 60)

    attendance.check_out = now
    attendance.check_out_lat = body.lat
    attendance.check_out_lng = body.lng
    attendance.total_minutes = total_minutes

    await db.commit()

    hours = total_minutes // 60
    mins = total_minutes % 60
    pay = None
    if current_user.hourly_rate:
        pay = round(current_user.hourly_rate * total_minutes / 60, 2)

    return {
        "ok": True,
        "check_out": now.isoformat(),
        "total_minutes": total_minutes,
        "display": f"{hours:02d}:{mins:02d}",
        "total_pay": pay,
        "message": f"יציאה נרשמה ✅ עבדת {hours}:{mins:02d} שעות",
    }


@router.get("/today")
async def get_today(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == current_user.id,
                Attendance.date == today,
            )
        )
    )
    att = result.scalar_one_or_none()
    if not att:
        return {"status": "not_checked_in"}

    now = datetime.now(timezone.utc)
    running_minutes = int((now - att.check_in).total_seconds() / 60) if not att.check_out else att.total_minutes

    return {
        "status": "checked_out" if att.check_out else "checked_in",
        "attendance_id": att.id,
        "check_in": att.check_in.isoformat(),
        "check_out": att.check_out.isoformat() if att.check_out else None,
        "total_minutes": att.total_minutes,
        "running_minutes": running_minutes,
        "is_valid_location": att.is_valid_location,
    }


@router.get("/my-history")
async def my_history(
    month: int | None = None,
    year: int | None = None,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    from_date = date(year, month, 1)
    if month == 12:
        to_date = date(year + 1, 1, 1)
    else:
        to_date = date(year, month + 1, 1)

    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == current_user.id,
                Attendance.date >= from_date,
                Attendance.date < to_date,
            )
        ).order_by(Attendance.date.desc())
    )
    records = result.scalars().all()

    total_minutes = sum(r.total_minutes or 0 for r in records)
    total_pay = None
    if current_user.hourly_rate:
        total_pay = round(current_user.hourly_rate * total_minutes / 60, 2)

    return {
        "month": month,
        "year": year,
        "total_minutes": total_minutes,
        "total_hours_display": f"{total_minutes // 60}:{total_minutes % 60:02d}",
        "total_pay": total_pay,
        "hourly_rate": current_user.hourly_rate,
        "records": [
            {
                "id": r.id,
                "date": r.date.isoformat(),
                "check_in": r.check_in.strftime("%H:%M"),
                "check_out": r.check_out.strftime("%H:%M") if r.check_out else None,
                "total_minutes": r.total_minutes,
                "hours_display": f"{(r.total_minutes or 0) // 60}:{(r.total_minutes or 0) % 60:02d}" if r.total_minutes else "—",
                "is_valid_location": r.is_valid_location,
            }
            for r in records
        ],
    }


# ──────────────────────────────────────────────
# Manager endpoints
# ──────────────────────────────────────────────

@router.get("/report")
async def attendance_report(
    month: int | None = None,
    year: int | None = None,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner"):
        raise HTTPException(status_code=403, detail="אין הרשאה")

    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year

    from_date = date(year, month, 1)
    if month == 12:
        to_date = date(year + 1, 1, 1)
    else:
        to_date = date(year, month + 1, 1)

    # Get all employees in org
    emp_result = await db.execute(
        select(Employee).where(
            and_(Employee.org_id == current_user.org_id, Employee.is_active == True)
        )
    )
    employees = emp_result.scalars().all()
    emp_map = {e.id: e for e in employees}

    # Get all attendance records
    att_result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.org_id == current_user.org_id,
                Attendance.date >= from_date,
                Attendance.date < to_date,
            )
        ).order_by(Attendance.date.desc())
    )
    records = att_result.scalars().all()

    # Group by employee
    by_employee: dict[str, list] = {}
    for r in records:
        by_employee.setdefault(r.employee_id, []).append(r)

    summary = []
    for emp in employees:
        recs = by_employee.get(emp.id, [])
        total_minutes = sum(r.total_minutes or 0 for r in recs)
        total_pay = None
        if emp.hourly_rate:
            total_pay = round(emp.hourly_rate * total_minutes / 60, 2)

        summary.append({
            "employee_id": emp.id,
            "employee_name": emp.name,
            "hourly_rate": emp.hourly_rate,
            "total_minutes": total_minutes,
            "total_hours_display": f"{total_minutes // 60}:{total_minutes % 60:02d}",
            "total_pay": total_pay,
            "days_worked": len(set(r.date for r in recs if r.check_out)),
            "records": [
                {
                    "date": r.date.isoformat(),
                    "check_in": r.check_in.strftime("%H:%M"),
                    "check_out": r.check_out.strftime("%H:%M") if r.check_out else "פתוח",
                    "total_minutes": r.total_minutes,
                    "hours_display": f"{(r.total_minutes or 0) // 60}:{(r.total_minutes or 0) % 60:02d}" if r.total_minutes else "—",
                    "is_valid_location": r.is_valid_location,
                }
                for r in sorted(recs, key=lambda x: x.date, reverse=True)
            ],
        })

    total_payroll = sum(e["total_pay"] or 0 for e in summary)

    return {
        "month": month,
        "year": year,
        "employees": summary,
        "total_payroll": round(total_payroll, 2),
    }


@router.get("/live")
async def live_attendance(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Who is currently checked in right now."""
    if current_user.role not in ("manager", "owner"):
        raise HTTPException(status_code=403, detail="אין הרשאה")

    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Attendance, Employee).join(
            Employee, Attendance.employee_id == Employee.id
        ).where(
            and_(
                Attendance.org_id == current_user.org_id,
                Attendance.date == today,
            )
        ).order_by(Attendance.check_in.desc())
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    return [
        {
            "employee_name": emp.name,
            "check_in": att.check_in.strftime("%H:%M"),
            "check_out": att.check_out.strftime("%H:%M") if att.check_out else None,
            "status": "יצא" if att.check_out else "בפנים",
            "running_minutes": int((now - att.check_in).total_seconds() / 60) if not att.check_out else att.total_minutes,
            "is_valid_location": att.is_valid_location,
        }
        for att, emp in rows
    ]
