"""
Orchestrates data loading → engine → result saving.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import (
    Employee, ShiftTemplate, ScheduleWeek, AvailabilitySubmission,
    ScheduledShift, FairnessTracking
)
from app.core.scheduler.engine import (
    ShiftScheduler, EmployeeData, ShiftSlot, ScheduleResult
)
import uuid
import logging

logger = logging.getLogger(__name__)

DAYS_MAP = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
# Python weekday (Mon=0) → our system (Sun=0)


def generate_schedule(
    db: Session,
    org_id: str,
    week_start: date,
    time_limit: int = 30,
) -> ScheduleResult:
    week_end = week_start + timedelta(days=6)

    # Get or create ScheduleWeek
    week = db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == org_id,
            ScheduleWeek.week_start == week_start,
        )
    ).scalar_one_or_none()

    if not week:
        week = ScheduleWeek(
            id=str(uuid.uuid4()),
            org_id=org_id,
            week_start=week_start,
            week_end=week_end,
            status="generating",
        )
        db.add(week)
        db.flush()
    else:
        week.status = "generating"
        # Delete existing optimizer assignments
        db.execute(
            ScheduledShift.__table__.delete().where(
                ScheduledShift.week_id == week.id,
                ScheduledShift.created_by == "optimizer",
            )
        )
        db.flush()

    # Load employees
    employees_db = db.execute(
        select(Employee).where(
            Employee.org_id == org_id,
            Employee.is_active == True,
        )
    ).scalars().all()

    # Load templates
    templates_db = db.execute(
        select(ShiftTemplate).where(
            ShiftTemplate.org_id == org_id,
            ShiftTemplate.is_active == True,
        )
    ).scalars().all()

    # Load availability submissions
    submissions = db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.week_id == week.id
        )
    ).scalars().all()
    submissions_by_emp = {s.employee_id: s for s in submissions}
    print(f"[scheduler] week_id={week.id} submissions_found={len(submissions)}", flush=True)
    for s in submissions:
        print(f"[scheduler] sub emp={s.employee_id} day_prefs={s.day_preferences}", flush=True)

    # Load fairness history (last 8 weeks)
    fairness_history = _load_fairness_history(db, org_id, week_start)

    # Build EmployeeData objects
    employee_data = []
    for emp in employees_db:
        sub = submissions_by_emp.get(emp.id)
        hard_blocked: set[str] = set()
        soft_blocked: set[str] = set()

        day_type_preferences: dict[int, list[str]] = {}

        if sub:
            for slot in sub.unavailability_slots:
                date_str = slot.date.isoformat()
                if slot.is_hard_constraint:
                    hard_blocked.add(date_str)
                else:
                    soft_blocked.add(date_str)

            # Build per-day type preferences from day_preferences JSON
            for day_str, pref in (sub.day_preferences or {}).items():
                day_idx = int(day_str)
                if pref.get("available", True):
                    types = pref.get("preferred_types", [])
                    if types:
                        day_type_preferences[day_idx] = types
                else:
                    # Not available this day — add to blocked sets
                    day_date = (week_start + timedelta(days=day_idx)).isoformat()
                    if pref.get("is_hard", True):
                        hard_blocked.add(day_date)
                    else:
                        soft_blocked.add(day_date)

        print(f"[scheduler] {emp.name}: sub={'yes' if sub else 'NO'} hard_blocked={hard_blocked} day_type_prefs={day_type_preferences}", flush=True)

        employee_data.append(EmployeeData(
            id=emp.id,
            name=emp.name,
            role=emp.role,
            max_hours_per_week=emp.max_hours_per_week,
            min_hours_per_week=emp.min_hours_per_week,
            max_consecutive_days=emp.max_consecutive_days,
            desired_shifts=sub.desired_shifts_count if sub and sub.desired_shifts_count else 3,
            preferred_shift_types=sub.preferred_shift_types if sub else [],
            hard_blocked_dates=hard_blocked,
            soft_blocked_dates=soft_blocked,
            historical_weekend_shifts=fairness_history.get(emp.id, {}).get("weekend_shifts", 0),
            historical_evening_shifts=fairness_history.get(emp.id, {}).get("evening_shifts", 0),
            day_type_preferences=day_type_preferences,
        ))

    # Build ShiftSlot objects for each day of the week
    shift_slots = []
    for template in templates_db:
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            # day_of_week: 0=Sun in our system
            dow = current_date.weekday()  # Mon=0
            # Convert: Mon=1, Tue=2, ..., Sun=0
            our_dow = (dow + 1) % 7
            if our_dow not in template.days_of_week:
                continue

            slot_id = str(uuid.uuid4())
            is_weekend = our_dow in (5, 6, 0)  # Fri, Sat, Sun

            shift_slots.append(ShiftSlot(
                id=slot_id,
                template_id=template.id,
                date=current_date.isoformat(),
                day_index=our_dow,
                start_time=template.start_time.strftime("%H:%M"),
                end_time=template.end_time.strftime("%H:%M"),
                duration_hours=template.duration_hours,
                shift_type=template.shift_type,
                min_employees=template.min_employees,
                max_employees=template.max_employees,
                required_roles=template.required_roles,
                is_weekend=is_weekend,
            ))

    if not shift_slots:
        raise ValueError("No shift slots generated — check shift templates and days_of_week")

    if not employee_data:
        raise ValueError("No active employees found")

    # Run optimizer
    scheduler = ShiftScheduler(
        employees=employee_data,
        shift_slots=shift_slots,
        week_start=week_start,
        fairness_history=fairness_history,
    )
    result = scheduler.build_and_solve(time_limit=time_limit)

    # Save assignments to DB
    slot_map = {s.id: s for s in shift_slots}
    for assignment in result.assignments:
        slot = slot_map[assignment.shift_slot_id]
        db.add(ScheduledShift(
            id=str(uuid.uuid4()),
            week_id=week.id,
            template_id=assignment.template_id,
            employee_id=assignment.employee_id,
            date=date.fromisoformat(assignment.date),
            start_time=_parse_time(slot.start_time),
            end_time=_parse_time(slot.end_time),
            status="assigned",
            is_manually_overridden=False,
            created_by="optimizer",
        ))

    # Update week record
    from datetime import datetime, timezone
    week.status = "generated"
    week.optimizer_score = result.score
    week.coverage_percent = result.coverage_percent
    week.generated_at = datetime.now(timezone.utc)
    week.optimizer_metadata = {
        "solver_status": result.solver_status,
        "solve_time": result.solve_time_seconds,
        "conflicts_count": len(result.conflicts),
        **result.metadata,
    }

    # Update fairness tracking
    _update_fairness_tracking(db, org_id, week.id, result.assignments, slot_map)

    db.commit()
    logger.info(
        f"Schedule generated: score={result.score}, coverage={result.coverage_percent}%, "
        f"assignments={len(result.assignments)}, status={result.solver_status}"
    )
    return result


def _load_fairness_history(db: Session, org_id: str, before_week: date) -> dict[str, dict]:
    lookback = before_week - timedelta(weeks=8)
    records = db.execute(
        select(FairnessTracking).join(ScheduleWeek).where(
            FairnessTracking.org_id == org_id,
            ScheduleWeek.week_start >= lookback,
            ScheduleWeek.week_start < before_week,
        )
    ).scalars().all()

    history: dict[str, dict] = {}
    for r in records:
        if r.employee_id not in history:
            history[r.employee_id] = {"weekend_shifts": 0, "evening_shifts": 0, "weeks": 0}
        history[r.employee_id]["weekend_shifts"] += r.weekend_shifts
        history[r.employee_id]["evening_shifts"] += r.evening_shifts
        history[r.employee_id]["weeks"] += 1

    # Convert to per-week averages
    for emp_id, data in history.items():
        weeks = max(data["weeks"], 1)
        data["weekend_shifts_per_week"] = data["weekend_shifts"] / weeks
        data["evening_shifts_per_week"] = data["evening_shifts"] / weeks

    return history


def _update_fairness_tracking(
    db: Session,
    org_id: str,
    week_id: str,
    assignments: list,
    slot_map: dict,
):
    from collections import defaultdict
    emp_stats: dict[str, dict] = defaultdict(
        lambda: {"total_hours": 0.0, "weekend_shifts": 0, "evening_shifts": 0, "morning_shifts": 0}
    )
    for a in assignments:
        slot = slot_map.get(a.shift_slot_id)
        if not slot:
            continue
        stats = emp_stats[a.employee_id]
        stats["total_hours"] += slot.duration_hours
        if slot.is_weekend:
            stats["weekend_shifts"] += 1
        if slot.shift_type == "evening":
            stats["evening_shifts"] += 1
        if slot.shift_type == "morning":
            stats["morning_shifts"] += 1

    for emp_id, stats in emp_stats.items():
        db.add(FairnessTracking(
            id=str(uuid.uuid4()),
            employee_id=emp_id,
            org_id=org_id,
            week_id=week_id,
            **stats,
        ))


def _parse_time(time_str: str):
    from datetime import time as dt_time
    h, m = map(int, time_str.split(":"))
    return dt_time(h, m)
