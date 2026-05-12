from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import AvailabilitySubmission, UnavailabilitySlot, ScheduleWeek
from app.api.v1.auth import get_current_user, Employee
import uuid
import os
import logging

logger = logging.getLogger(__name__)

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


@router.post("/send-reminders")
async def send_availability_reminders(
    week_start: date,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if current_user.role not in ("manager", "owner", "super_admin"):
            raise HTTPException(status_code=403)

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

        twilio_keys = [k for k in os.environ if 'TWILIO' in k]
        print(f"[send-reminders] TWILIO keys in env: {twilio_keys}", flush=True)
        print(f"[send-reminders] sid={'SET' if account_sid else 'MISSING'} token={'SET' if auth_token else 'MISSING'} from={whatsapp_number}", flush=True)

        if not account_sid or not auth_token:
            raise HTTPException(status_code=500, detail="Twilio credentials not configured")

        import httpx
        from app.models import Employee as EmpModel

        employees = (await db.execute(
            select(EmpModel).where(
                EmpModel.org_id == current_user.org_id,
                EmpModel.is_active == True,
                EmpModel.phone != None,
            )
        )).scalars().all()

        print(f"[send-reminders] found {len(employees)} employees with phone", flush=True)

        week = (await db.execute(
            select(ScheduleWeek).where(
                ScheduleWeek.org_id == current_user.org_id,
                ScheduleWeek.week_start == week_start,
            )
        )).scalar_one_or_none()

        submitted_ids = set()
        if week:
            subs = (await db.execute(
                select(AvailabilitySubmission).where(
                    AvailabilitySubmission.week_id == week.id
                )
            )).scalars().all()
            submitted_ids = {s.employee_id for s in subs}

        sent, failed = 0, 0
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        async with httpx.AsyncClient() as client:
            for emp in employees:
                if emp.id in submitted_ids:
                    continue
                phone = emp.phone.replace("-", "").replace(" ", "")
                if not phone.startswith("+"):
                    phone = "+972" + phone.lstrip("0")
                try:
                    resp = await client.post(
                        twilio_url,
                        auth=(account_sid, auth_token),
                        data={
                            "From": f"whatsapp:{whatsapp_number}",
                            "To": f"whatsapp:{phone}",
                            "Body": (
                                f"שלום {emp.name} 👋\n"
                                f"טרם הגשת זמינות לשבוע {week_start.strftime('%d/%m')}.\n"
                                f"שלח *זמינות* כדי להגיש עכשיו."
                            ),
                        },
                    )
                    print(f"[send-reminders] Twilio {resp.status_code} for {phone}: {resp.text[:200]}", flush=True)
                    if resp.status_code == 201:
                        sent += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"[send-reminders] exception sending to {phone}: {e}", flush=True)
                    failed += 1

        return {"sent": sent, "failed": failed, "skipped": len(submitted_ids)}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[send-reminders] FATAL: {type(e).__name__}: {e}\n{tb}", flush=True)
        return {"error": f"{type(e).__name__}: {str(e)}", "sent": 0, "failed": 0, "skipped": 0}


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


@router.get("/manager-view")
async def get_manager_availability_view(
    week_start: date,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all employees' availability for a given week (manager only)."""
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    from app.models import Employee as EmpModel
    employees = (await db.execute(
        select(EmpModel).where(
            EmpModel.org_id == current_user.org_id,
            EmpModel.is_active == True,
        ).order_by(EmpModel.name)
    )).scalars().all()

    week = (await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == current_user.org_id,
            ScheduleWeek.week_start == week_start,
        )
    )).scalar_one_or_none()

    submissions_by_emp = {}
    if week:
        subs = (await db.execute(
            select(AvailabilitySubmission).where(
                AvailabilitySubmission.week_id == week.id
            )
        )).scalars().all()
        submissions_by_emp = {s.employee_id: s for s in subs}

    result = []
    for emp in employees:
        sub = submissions_by_emp.get(emp.id)
        result.append({
            "employee_id": emp.id,
            "employee_name": emp.name,
            "submitted": sub is not None,
            "submitted_at": sub.submitted_at.isoformat() if sub else None,
            "day_preferences": sub.day_preferences if sub else {},
        })

    return {"week_start": week_start.isoformat(), "employees": result}


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
