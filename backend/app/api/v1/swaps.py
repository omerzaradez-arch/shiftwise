from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import SwapRequest, ScheduledShift, Employee
from app.api.v1.auth import get_current_user
import uuid

router = APIRouter()


class SwapRequestBody(BaseModel):
    shift_id: str
    reason: str = ""
    target_employee_id: str | None = None


@router.post("/request")
async def request_swap(
    req: SwapRequestBody,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shift = await db.get(ScheduledShift, req.shift_id)
    if not shift or shift.employee_id != current_user.id:
        raise HTTPException(status_code=404, detail="משמרת לא נמצאה")

    swap = SwapRequest(
        id=str(uuid.uuid4()),
        shift_id=req.shift_id,
        requester_id=current_user.id,
        target_employee_id=req.target_employee_id,
        reason=req.reason,
        status="pending",
    )
    db.add(swap)
    shift.status = "swap_requested"
    await db.commit()

    # Send push notification to managers
    try:
        from app.core.push import send_push_to_managers
        dow = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"][(shift.date.weekday() + 1) % 7]
        await send_push_to_managers(
            org_id=current_user.org_id,
            title="🔄 בקשת החלפה חדשה",
            body=f"{current_user.name} מבקש/ת החלפה ליום {dow} {shift.date.strftime('%d/%m')}",
            url="/requests",
        )
    except Exception as e:
        print(f"[push] failed: {e}", flush=True)

    return {"id": swap.id, "status": "pending"}


@router.get("/pending")
async def get_pending_swaps(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    swaps = (await db.execute(
        select(SwapRequest, ScheduledShift, Employee)
        .join(ScheduledShift, SwapRequest.shift_id == ScheduledShift.id)
        .join(Employee, SwapRequest.requester_id == Employee.id)
        .where(
            SwapRequest.status == "pending",
            Employee.org_id == current_user.org_id,
        )
        .order_by(SwapRequest.created_at.desc())
    )).all()

    return [
        {
            "id": swap.id,
            "shift": {
                "id": shift.id,
                "date": shift.date.isoformat(),
                "start_time": shift.start_time.strftime("%H:%M"),
                "end_time": shift.end_time.strftime("%H:%M"),
            },
            "requester": {"id": emp.id, "name": emp.name},
            "reason": swap.reason,
            "created_at": swap.created_at.isoformat(),
        }
        for swap, shift, emp in swaps
    ]


@router.post("/{swap_id}/approve")
async def approve_swap(
    swap_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    swap = await db.get(SwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404)

    swap.status = "approved"
    swap.reviewed_by = current_user.id

    shift = await db.get(ScheduledShift, swap.shift_id)
    if shift and swap.target_employee_id:
        shift.employee_id = swap.target_employee_id
        shift.status = "swap_approved"
        shift.is_manually_overridden = True

    await db.commit()
    return {"status": "approved"}


@router.post("/{swap_id}/reject")
async def reject_swap(
    swap_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    swap = await db.get(SwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404)

    swap.status = "rejected"
    swap.reviewed_by = current_user.id

    shift = await db.get(ScheduledShift, swap.shift_id)
    if shift:
        shift.status = "assigned"

    await db.commit()
    return {"status": "rejected"}


@router.get("/suggestions/{shift_id}")
async def get_swap_suggestions(
    shift_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find best replacement candidates for a swap."""
    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404)

    from app.models import AvailabilitySubmission, ScheduleWeek
    week = await db.get(ScheduleWeek, shift.week_id)

    all_emps = (await db.execute(
        select(Employee).where(
            Employee.org_id == current_user.org_id,
            Employee.is_active == True,
            Employee.id != shift.employee_id,
        )
    )).scalars().all()

    already_working = {
        s.employee_id for s in (await db.execute(
            select(ScheduledShift).where(
                ScheduledShift.week_id == shift.week_id,
                ScheduledShift.date == shift.date,
                ScheduledShift.status != "cancelled",
            )
        )).scalars().all()
    }

    candidates = []
    for emp in all_emps:
        if emp.id in already_working:
            continue
        candidates.append({
            "employee_id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "fit_score": 100 if emp.role == "senior" else 70,
        })

    return sorted(candidates, key=lambda c: c["fit_score"], reverse=True)[:5]
