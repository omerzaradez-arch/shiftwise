import uuid
from datetime import date, time
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


class CreateShiftRequest(BaseModel):
    week_start: date
    date: date
    template_id: str
    employee_id: str
    start_time: time | None = None
    end_time: time | None = None


class UpdateShiftRequest(BaseModel):
    employee_id: str | None = None
    date: date | None = None
    template_id: str | None = None
    start_time: time | None = None
    end_time: time | None = None


def _require_manager(user: Employee):
    if user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)


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
    _require_manager(current_user)

    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404)

    shift.employee_id = req.employee_id
    shift.date = req.date
    shift.is_manually_overridden = True
    await db.commit()

    return {"status": "moved"}


@router.post("/")
async def create_shift(
    req: CreateShiftRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a shift. Creates the schedule week if it doesn't exist."""
    _require_manager(current_user)

    template = await db.get(ShiftTemplate, req.template_id)
    if not template or template.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Template not found")

    employee = await db.get(Employee, req.employee_id)
    if not employee or employee.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    from datetime import timedelta
    week = (await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == current_user.org_id,
            ScheduleWeek.week_start == req.week_start,
        )
    )).scalar_one_or_none()

    if not week:
        week = ScheduleWeek(
            id=str(uuid.uuid4()),
            org_id=current_user.org_id,
            week_start=req.week_start,
            week_end=req.week_start + timedelta(days=6),
            status="collecting",
        )
        db.add(week)
        await db.flush()

    shift = ScheduledShift(
        id=str(uuid.uuid4()),
        week_id=week.id,
        template_id=req.template_id,
        employee_id=req.employee_id,
        date=req.date,
        start_time=req.start_time or template.start_time,
        end_time=req.end_time or template.end_time,
        status="assigned",
        is_manually_overridden=True,
        created_by="manager",
    )
    db.add(shift)
    await db.commit()

    return {
        "id": shift.id,
        "date": shift.date.isoformat(),
        "start_time": shift.start_time.strftime("%H:%M"),
        "end_time": shift.end_time.strftime("%H:%M"),
        "employee_id": shift.employee_id,
        "template_id": shift.template_id,
    }


@router.patch("/{shift_id}")
async def update_shift(
    shift_id: str,
    req: UpdateShiftRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(current_user)

    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404)

    if req.employee_id is not None:
        emp = await db.get(Employee, req.employee_id)
        if not emp or emp.org_id != current_user.org_id:
            raise HTTPException(status_code=404, detail="Employee not found")
        shift.employee_id = req.employee_id
    if req.date is not None:
        shift.date = req.date
    if req.template_id is not None:
        tmpl = await db.get(ShiftTemplate, req.template_id)
        if not tmpl or tmpl.org_id != current_user.org_id:
            raise HTTPException(status_code=404, detail="Template not found")
        shift.template_id = req.template_id
        # If new template, also update times unless explicitly provided
        if req.start_time is None:
            shift.start_time = tmpl.start_time
        if req.end_time is None:
            shift.end_time = tmpl.end_time
    if req.start_time is not None:
        shift.start_time = req.start_time
    if req.end_time is not None:
        shift.end_time = req.end_time

    shift.is_manually_overridden = True
    await db.commit()
    return {"status": "updated"}


@router.delete("/{shift_id}")
async def delete_shift(
    shift_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(current_user)

    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404)

    await db.delete(shift)
    await db.commit()
    return {"status": "deleted"}
