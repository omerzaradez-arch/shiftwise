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
        "debug": result.metadata.get("_debug_day_prefs", {}),
        "debug_submissions": result.metadata.get("_debug_submissions_count", -1),
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
    background_tasks: BackgroundTasks,
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

    # Load shifts with employee info for notifications
    shifts_result = await db.execute(
        select(ScheduledShift)
        .where(ScheduledShift.week_id == schedule_id)
        .where(ScheduledShift.status != "cancelled")
    )
    shifts = shifts_result.scalars().all()

    # Group shifts by employee
    by_employee: dict[str, list[ScheduledShift]] = {}
    for shift in shifts:
        by_employee.setdefault(shift.employee_id, []).append(shift)

    # Load all relevant employees
    emp_ids = list(by_employee.keys())
    employees_result = await db.execute(
        select(Employee).where(Employee.id.in_(emp_ids))
    )
    employees = {e.id: e for e in employees_result.scalars().all()}

    DAY_NAMES = {0: "ראשון", 1: "שני", 2: "שלישי", 3: "רביעי", 4: "חמישי", 5: "שישי", 6: "שבת"}
    SHIFT_NAMES = {"morning": "בוקר", "afternoon": "אחהצ", "evening": "ערב", "night": "לילה"}

    # Build shifts_by_day for image generation
    all_emp_result = await db.execute(
        select(Employee).where(Employee.org_id == current_user.org_id, Employee.is_active == True)
    )
    all_employees_map = {e.id: e for e in all_emp_result.scalars().all()}

    shifts_by_day: dict = {}
    operating_days_set: set = set()
    for shift in shifts:
        d = shift.date.isoformat()
        st = shift.start_time
        shift_type = "morning" if st.hour < 12 else "evening"
        emp_name = all_employees_map.get(shift.employee_id, type("", (), {"name": "?"})()).name
        shifts_by_day.setdefault(d, {}).setdefault(shift_type, []).append(emp_name)
        dow = (shift.date.weekday() + 1) % 7
        operating_days_set.add(dow)

    operating_days = sorted(operating_days_set)

    background_tasks.add_task(
        _send_schedule_notifications,
        employees, by_employee, week, all_employees_map,
        shifts_by_day, operating_days, schedule_id,
    )

    return {"status": "published", "notified": len(emp_ids)}


# ── Serve schedule image (no auth — URL is unguessable enough for WhatsApp) ──
_image_cache: dict[str, bytes] = {}

@router.get("/{schedule_id}/image.png", include_in_schema=False)
async def get_schedule_image(schedule_id: str):
    from fastapi.responses import Response
    img_bytes = _image_cache.get(schedule_id)
    if not img_bytes:
        raise HTTPException(status_code=404, detail="תמונה לא נמצאה")
    return Response(content=img_bytes, media_type="image/png")


async def _send_schedule_notifications(
    employees, by_employee, week, all_employees_map,
    shifts_by_day, operating_days, schedule_id,
):
    print(f"[notify] starting — {len(all_employees_map)} employees", flush=True)
    try:
        from app.api.v1.whatsapp import send_whatsapp_to
        from app.core.schedule_image import ensure_font, generate_schedule_image
        from app.config import settings
    except Exception as e:
        print(f"[notify] import error: {e}", flush=True)
        return

    week_str = week.week_start.strftime("%d/%m")

    # Generate schedule image
    await ensure_font()
    try:
        img_bytes = generate_schedule_image(week.week_start, shifts_by_day, operating_days)
        _image_cache[schedule_id] = img_bytes
        image_url = f"{settings.backend_url}/api/v1/schedules/{schedule_id}/image.png"
        print(f"[notify] image generated ok, url={image_url}", flush=True)
    except Exception as e:
        print(f"[notify] image failed: {e}", flush=True)
        image_url = None

    # Send to all employees with phones
    notified = set()
    for emp in all_employees_map.values():
        if not emp.phone or emp.id in notified:
            print(f"[notify] skipping {emp.name} — no phone or already notified", flush=True)
            continue
        print(f"[notify] sending to {emp.name} ({emp.phone})", flush=True)

        my_shifts = by_employee.get(emp.id, [])
        my_shifts_sorted = sorted(my_shifts, key=lambda s: s.date)
        DAY_NAMES = {0: "ראשון", 1: "שני", 2: "שלישי", 3: "רביעי", 4: "חמישי", 5: "שישי", 6: "שבת"}

        if my_shifts_sorted:
            lines = []
            for s in my_shifts_sorted:
                day_name = DAY_NAMES.get((s.date.weekday() + 1) % 7, "")
                lines.append(f"• {day_name} {s.date.strftime('%d/%m')}: {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}")
            personal = "המשמרות שלך:\n" + "\n".join(lines)
        else:
            personal = "אין לך משמרות השבוע."

        view_url = f"{settings.frontend_url}/view/{week.org_id}"

        msg = (
            f"שלום {emp.name} 👋\n"
            f"הסידור לשבוע {week_str} פורסם!\n\n"
            f"{personal}\n\n"
            f"📅 לצפייה בסידור המלא:\n{view_url}\n\n"
            f"שלח *לא יכול* אם יש בעיה עם משמרת."
        )

        try:
            ok = await send_whatsapp_to(emp.phone, msg)
            print(f"[notify] sent to {emp.name}: {'ok' if ok else 'failed'}", flush=True)
        except Exception as e:
            print(f"[notify] error sending to {emp.name}: {e}", flush=True)
        notified.add(emp.id)

    print(f"[notify] done — notified {len(notified)} employees", flush=True)


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
