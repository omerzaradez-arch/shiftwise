from datetime import date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db, SyncSessionLocal
from app.models import ScheduleWeek, ScheduledShift, Employee, ShiftTemplate
from app.api.v1.auth import get_current_user
from app.core.scheduler import service as scheduler_service
import uuid

router = APIRouter()


class GenerateRequest(BaseModel):
    week_start: date


@router.post("/generate")
async def generate_schedule(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print(f"[generate] POST received user={current_user.name} week={req.week_start}", flush=True)
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="אין הרשאה")

    # Run in background (sync session for OR-Tools)
    background_tasks.add_task(
        _run_optimizer_sync,
        org_id=current_user.org_id,
        week_start=req.week_start,
    )

    return {"status": "started", "message": "האופטימייזר רץ ברקע"}


def _run_optimizer_sync(org_id: str, week_start: date):
    print(f"[optimizer] START org={org_id} week={week_start}", flush=True)
    with SyncSessionLocal() as db:
        try:
            result = scheduler_service.generate_schedule(
                db=db,
                org_id=org_id,
                week_start=week_start,
            )
            print(f"[optimizer] DONE score={result.score}", flush=True)
            return result
        except Exception as e:
            print(f"[optimizer] ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise


@router.post("/generate/sync")
async def generate_schedule_sync(
    req: GenerateRequest,
    current_user: Employee = Depends(get_current_user),
):
    """Synchronous endpoint for development/testing."""
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="אין הרשאה")

    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _run_optimizer_sync_result(current_user.org_id, req.week_start),
    )
    return {
        "score": result.score,
        "coverage": result.coverage_percent,
        "conflicts": len(result.conflicts),
        "assignments": len(result.assignments),
        "solver_status": result.solver_status,
    }


def _run_optimizer_sync_result(org_id: str, week_start: date):
    with SyncSessionLocal() as db:
        return scheduler_service.generate_schedule(db=db, org_id=org_id, week_start=week_start)


@router.get("/week")
async def get_week_schedule(
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
        raise HTTPException(status_code=404, detail="לא נמצא סידור לשבוע זה")

    shifts = (await db.execute(
        select(ScheduledShift, Employee, ShiftTemplate)
        .join(Employee, ScheduledShift.employee_id == Employee.id)
        .join(ShiftTemplate, ScheduledShift.template_id == ShiftTemplate.id)
        .where(ScheduledShift.week_id == week.id)
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
    )).all()

    return {
        "id": week.id,
        "week_start": week.week_start.isoformat(),
        "week_end": week.week_end.isoformat(),
        "status": week.status,
        "optimizer_score": week.optimizer_score,
        "coverage_percent": week.coverage_percent,
        "generated_at": week.generated_at.isoformat() if week.generated_at else None,
        "published_at": week.published_at.isoformat() if week.published_at else None,
        "shifts": [
            {
                "id": s.id,
                "date": s.date.isoformat(),
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "duration_hours": template.duration_hours,
                "shift_name": template.name,
                "shift_type": template.shift_type,
                "employee_id": emp.id,
                "employee_name": emp.name,
                "employee_role": emp.role,
                "status": s.status,
                "is_manually_overridden": s.is_manually_overridden,
            }
            for s, emp, template in shifts
        ],
    }


@router.post("/{schedule_id}/publish")
async def publish_schedule(
    schedule_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="אין הרשאה")

    week = await db.get(ScheduleWeek, schedule_id)
    if not week or week.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="לא נמצא")

    from datetime import datetime, timezone
    week.status = "published"
    week.published_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "published"}


@router.get("/conflicts")
async def get_conflicts(
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

    conflicts = week.optimizer_metadata.get("conflicts", [])
    return [
        {
            "id": str(uuid.uuid4()),
            "type": c.get("type"),
            "type_label": _conflict_label(c.get("type")),
            "severity": c.get("severity", "medium"),
            "date": c.get("date", ""),
            "description": c.get("description", ""),
            "suggestion": c.get("suggestion"),
            "affected_employee_ids": [c.get("employee_id")] if c.get("employee_id") else [],
        }
        for c in conflicts
    ]


def _conflict_label(conflict_type: str | None) -> str:
    labels = {
        "close_open": "סגירה + פתיחה ברצף",
        "under_coverage": "כיסוי חסר",
        "no_senior": "אין עובד בכיר",
        "overload": "עומס יתר",
    }
    return labels.get(conflict_type or "", conflict_type or "קונפליקט")
