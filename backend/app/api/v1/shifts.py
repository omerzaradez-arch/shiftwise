from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import ScheduledShift, ScheduleWeek, ShiftTemplate, Employee
from app.api.v1.auth import get_current_user

router = APIRouter()


class MoveShiftRequest(BaseModel):
    employee_id: str
    date: date


@router.get("/my")
async def get_my_shifts(
    week_start: date,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week = (await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == current_user.org_id,
            ScheduleWeek.week_start == week_start,
        )
    )).scalar_one_or_none()

    if not week:
        return []

    shifts = (await db.execute(
        select(ScheduledShift, ShiftTemplate)
        .join(ShiftTemplate, ScheduledShift.template_id == ShiftTemplate.id)
        .where(
            ScheduledShift.week_id == week.id,
            ScheduledShift.employee_id == current_user.id,
            ScheduledShift.status != "cancelled",
        )
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
    )).all()

    return [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "duration_hours": template.duration_hours,
            "shift_name": template.name,
            "shift_type": template.shift_type,
            "employee_id": current_user.id,
            "employee_name": current_user.name,
            "employee_role": current_user.role,
            "status": s.status,
            "is_manually_overridden": s.is_manually_overridden,
        }
        for s, template in shifts
    ]


@router.get("/next")
async def get_next_shift(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()

    result = (await db.execute(
        select(ScheduledShift, ShiftTemplate)
        .join(ShiftTemplate, ScheduledShift.template_id == ShiftTemplate.id)
        .join(ScheduleWeek, ScheduledShift.week_id == ScheduleWeek.id)
        .where(
            ScheduledShift.employee_id == current_user.id,
            ScheduledShift.date >= today,
            ScheduledShift.status == "assigned",
            ScheduleWeek.status == "published",
        )
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
        .limit(1)
    )).first()

    if not result:
        return None

    s, template = result
    return {
        "id": s.id,
        "date": s.date.isoformat(),
        "start_time": s.start_time.strftime("%H:%M"),
        "end_time": s.end_time.strftime("%H:%M"),
        "shift_name": template.name,
        "shift_type": template.shift_type,
    }


@router.patch("/{shift_id}/move")
async def move_shift(
    shift_id: str,
    req: MoveShiftRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404)

    shift.employee_id = req.employee_id
    shift.date = req.date
    shift.is_manually_overridden = True
    await db.commit()

    return {"status": "moved"}
