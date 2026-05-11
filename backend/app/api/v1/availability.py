from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import AvailabilitySubmission, UnavailabilitySlot, ScheduleWeek
from app.api.v1.auth import get_current_user, Employee
import uuid

router = APIRouter()


class AvailabilityRequest(BaseModel):
    week_start: date
    blocked_days: list[int]       # 0=Sun ... 6=Sat
    desired_shifts_count: int
    preferred_shift_types: list[str]
    notes: str = ""


@router.post("/submit")
async def submit_availability(
    req: AvailabilityRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week_end = req.week_start + timedelta(days=6)

    # Get or create week
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
            week_end=week_end,
            status="collecting",
        )
        db.add(week)
        await db.flush()

    # Delete existing submission
    existing = (await db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.employee_id == current_user.id,
            AvailabilitySubmission.week_id == week.id,
        )
    )).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.flush()

    # Create new submission
    submission = AvailabilitySubmission(
        id=str(uuid.uuid4()),
        employee_id=current_user.id,
        week_id=week.id,
        desired_shifts_count=req.desired_shifts_count,
        preferred_shift_types=req.preferred_shift_types,
        notes=req.notes,
    )
    db.add(submission)
    await db.flush()

    # Create unavailability slots for blocked days
    for day_index in req.blocked_days:
        blocked_date = req.week_start + timedelta(days=day_index)
        db.add(UnavailabilitySlot(
            id=str(uuid.uuid4()),
            submission_id=submission.id,
            date=blocked_date,
            is_hard_constraint=True,
        ))

    await db.commit()
    return {"status": "submitted", "submission_id": submission.id}


@router.get("/my")
async def get_my_availability(
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
        raise HTTPException(status_code=404)

    sub = (await db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.employee_id == current_user.id,
            AvailabilitySubmission.week_id == week.id,
        )
    )).scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404)

    return {
        "id": sub.id,
        "desired_shifts_count": sub.desired_shifts_count,
        "preferred_shift_types": sub.preferred_shift_types,
        "notes": sub.notes,
        "blocked_dates": [s.date.isoformat() for s in sub.unavailability_slots],
        "submitted_at": sub.submitted_at.isoformat(),
    }


@router.get("/week-status")
async def get_week_status(
    week_start: date,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns how many employees have submitted availability."""
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    week = (await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == current_user.org_id,
            ScheduleWeek.week_start == week_start,
        )
    )).scalar_one_or_none()

    if not week:
        return {"submitted": 0, "total": 0}

    from app.models import Employee as EmpModel
    total = (await db.execute(
        select(EmpModel).where(
            EmpModel.org_id == current_user.org_id,
            EmpModel.is_active == True,
        )
    )).scalars().all()

    submitted = (await db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.week_id == week.id
        )
    )).scalars().all()

    return {"submitted": len(submitted), "total": len(total)}
