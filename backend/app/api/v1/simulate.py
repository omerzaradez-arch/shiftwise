"""Simulation endpoint — runs test scenarios against the scheduling engine."""
from fastapi import APIRouter, Depends
from datetime import date, timedelta
import copy

from app.core.scheduler.engine import ShiftScheduler, EmployeeData, ShiftSlot

router = APIRouter()

WEEK_START = date(2026, 5, 17)


def _make_slots():
    slots = []
    for day_offset in range(6):
        d = WEEK_START + timedelta(days=day_offset)
        our_dow = (d.weekday() + 1) % 7
        is_weekend = our_dow in (0, 5, 6)
        for shift_type, start, end in [("morning", "07:00", "15:00"), ("evening", "15:00", "23:00")]:
            slots.append(ShiftSlot(
                id=f"{shift_type}_{day_offset}",
                template_id=f"tmpl_{shift_type}",
                date=d.isoformat(),
                day_index=our_dow,
                start_time=start, end_time=end,
                duration_hours=8.0,
                shift_type=shift_type,
                min_employees=2, max_employees=4,
                required_roles={"senior": 1},
                is_weekend=is_weekend,
            ))
    return slots


def _make_employees():
    fri = (WEEK_START + timedelta(days=5)).isoformat()
    wed = (WEEK_START + timedelta(days=3)).isoformat()
    return [
        EmployeeData(id="e1", name="דינה (בכירה-ערב)", role="senior",
                     max_hours_per_week=40, min_hours_per_week=16, max_consecutive_days=5,
                     desired_shifts=4, preferred_shift_types=["evening"],
                     hard_blocked_dates=set(), soft_blocked_dates=set(),
                     day_type_preferences={i: ["evening"] for i in range(6)}),
        EmployeeData(id="e2", name="יוסי (ללא סוף שבוע)", role="junior",
                     max_hours_per_week=40, min_hours_per_week=16, max_consecutive_days=5,
                     desired_shifts=4, preferred_shift_types=["morning"],
                     hard_blocked_dates={fri}, soft_blocked_dates=set(), day_type_preferences={}),
        EmployeeData(id="e3", name="מיכל (בכירה-מינימום)", role="senior",
                     max_hours_per_week=20, min_hours_per_week=0, max_consecutive_days=3,
                     desired_shifts=2, preferred_shift_types=["morning"],
                     hard_blocked_dates=set(), soft_blocked_dates=set(), day_type_preferences={}),
        EmployeeData(id="e4", name="רן (גמיש)", role="junior",
                     max_hours_per_week=48, min_hours_per_week=24, max_consecutive_days=6,
                     desired_shifts=5, preferred_shift_types=[],
                     hard_blocked_dates=set(), soft_blocked_dates=set(), day_type_preferences={}),
        EmployeeData(id="e5", name="נועה (מתמחה-בוקר)", role="trainee",
                     max_hours_per_week=32, min_hours_per_week=16, max_consecutive_days=5,
                     desired_shifts=4, preferred_shift_types=["morning"],
                     hard_blocked_dates=set(), soft_blocked_dates=set(),
                     day_type_preferences={i: ["morning"] for i in range(6)}),
        EmployeeData(id="e6", name="אבי (חסום רביעי)", role="junior",
                     max_hours_per_week=40, min_hours_per_week=16, max_consecutive_days=4,
                     desired_shifts=4, preferred_shift_types=["evening"],
                     hard_blocked_dates={wed}, soft_blocked_dates=set(), day_type_preferences={}),
        EmployeeData(id="e7", name="טל (מנהל-גמיש)", role="manager",
                     max_hours_per_week=56, min_hours_per_week=32, max_consecutive_days=6,
                     desired_shifts=6, preferred_shift_types=[],
                     hard_blocked_dates=set(), soft_blocked_dates=set(), day_type_preferences={}),
        EmployeeData(id="e8", name="גל (מינימום-בוקר)", role="junior",
                     max_hours_per_week=24, min_hours_per_week=0, max_consecutive_days=3,
                     desired_shifts=2, preferred_shift_types=["morning"],
                     hard_blocked_dates=set(), soft_blocked_dates={fri}, day_type_preferences={}),
    ]


def _run(label, employees, slots):
    scheduler = ShiftScheduler(employees=employees, shift_slots=slots,
                               week_start=WEEK_START, fairness_history={})
    result = scheduler.build_and_solve(time_limit=10)

    emp_map = {e.id: e for e in employees}
    counts = {e.id: 0 for e in employees}
    hours = {e.id: 0.0 for e in employees}
    pref_violations = {e.id: 0 for e in employees}

    for a in result.assignments:
        counts[a.employee_id] += 1
        slot = next(s for s in slots if s.id == a.shift_slot_id)
        hours[a.employee_id] += slot.duration_hours
        emp = emp_map[a.employee_id]
        day_prefs = emp.day_type_preferences.get(slot.day_index)
        if day_prefs and slot.shift_type not in day_prefs:
            pref_violations[a.employee_id] += 1

    return {
        "scenario": label,
        "solver_status": result.solver_status,
        "score": result.score,
        "coverage_percent": result.coverage_percent,
        "conflicts": len(result.conflicts),
        "assignments": len(result.assignments),
        "per_employee": [
            {
                "name": e.name,
                "shifts": counts[e.id],
                "hours": hours[e.id],
                "preference_violations": pref_violations[e.id],
            }
            for e in employees
        ],
        "conflict_details": result.conflicts[:5],
    }


@router.get("/run")
async def run_simulation():
    slots = _make_slots()
    employees = _make_employees()
    sun = WEEK_START.isoformat()
    mon = (WEEK_START + timedelta(days=1)).isoformat()

    scenarios = []

    # 1. Base
    scenarios.append(_run("בסיס — 8 עובדים", employees, slots))

    # 2. Last-minute cancellation
    emp2 = copy.deepcopy(employees)
    for e in emp2:
        if e.id == "e6":
            e.hard_blocked_dates.add(sun)
    scenarios.append(_run("ביטול ברגע אחרון (אבי מוסיף ראשון)", emp2, slots))

    # 3. New employee
    emp3 = list(employees) + [
        EmployeeData(id="e9", name="חדש", role="junior",
                     max_hours_per_week=32, min_hours_per_week=8, max_consecutive_days=5,
                     desired_shifts=3, preferred_shift_types=["morning"],
                     hard_blocked_dates=set(), soft_blocked_dates=set(), day_type_preferences={})
    ]
    scenarios.append(_run("עובד חדש מצטרף", emp3, slots))

    # 4. Senior suddenly unavailable
    emp4 = copy.deepcopy(employees)
    for e in emp4:
        if e.id == "e1":
            e.hard_blocked_dates.update({sun, mon})
    scenarios.append(_run("בכירה חוסמת ראשון+שני", emp4, slots))

    # 5. Minimal staff
    scenarios.append(_run("צוות מינימלי (4 עובדים)", employees[:4], slots))

    return {"week_start": WEEK_START.isoformat(), "scenarios": scenarios}
