"""Public endpoints — no authentication required."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta

from app.database import get_db
from app.models import Employee, ScheduleWeek, ScheduledShift, Organization

router = APIRouter()

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
