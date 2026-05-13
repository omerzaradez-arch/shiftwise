print("טוען...", flush=True)
"""
Simulation script for ShiftWise scheduling engine.
Tests 8 fictional employees with varied constraints, availability, and preferences.
Run from backend/: python simulate.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from app.core.scheduler.engine import ShiftScheduler, EmployeeData, ShiftSlot

WEEK_START = date(2026, 5, 17)  # Sunday

# ── Shift slots (2 templates × 6 days) ────────────────────────────────────────
def make_slots():
    slots = []
    for day_offset in range(6):  # Sun–Fri
        d = WEEK_START + timedelta(days=day_offset)
        our_dow = (d.weekday() + 1) % 7  # 0=Sun
        is_weekend = our_dow in (0, 5, 6)

        # Morning slot
        slots.append(ShiftSlot(
            id=f"morning_{day_offset}",
            template_id="tmpl_morning",
            date=d.isoformat(),
            day_index=our_dow,
            start_time="07:00", end_time="15:00",
            duration_hours=8.0,
            shift_type="morning",
            min_employees=2, max_employees=4,
            required_roles={"senior": 1},
            is_weekend=is_weekend,
        ))
        # Evening slot
        slots.append(ShiftSlot(
            id=f"evening_{day_offset}",
            template_id="tmpl_evening",
            date=d.isoformat(),
            day_index=our_dow,
            start_time="15:00", end_time="23:00",
            duration_hours=8.0,
            shift_type="evening",
            min_employees=2, max_employees=4,
            required_roles={"senior": 1},
            is_weekend=is_weekend,
        ))
    return slots

# ── 8 fictional employees ──────────────────────────────────────────────────────
def make_employees():
    fri = (WEEK_START + timedelta(days=5)).isoformat()  # Friday
    sat = (WEEK_START + timedelta(days=6)).isoformat()  # Saturday
    wed = (WEEK_START + timedelta(days=3)).isoformat()  # Wednesday

    return [
        # 1. דינה — senior, evenings only (hard)
        EmployeeData(
            id="emp_dina", name="דינה", role="senior",
            max_hours_per_week=40, min_hours_per_week=16,
            max_consecutive_days=5, desired_shifts=4,
            preferred_shift_types=["evening"],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={0: ["evening"], 1: ["evening"], 2: ["evening"],
                                   3: ["evening"], 4: ["evening"], 5: ["evening"]},
        ),
        # 2. יוסי — junior, not available Fri/Sat (hard block)
        EmployeeData(
            id="emp_yossi", name="יוסי", role="junior",
            max_hours_per_week=40, min_hours_per_week=16,
            max_consecutive_days=5, desired_shifts=4,
            preferred_shift_types=["morning", "afternoon"],
            hard_blocked_dates={fri, sat}, soft_blocked_dates=set(),
            day_type_preferences={},
        ),
        # 3. מיכל — senior, wants minimal shifts (2/week)
        EmployeeData(
            id="emp_michal", name="מיכל", role="senior",
            max_hours_per_week=20, min_hours_per_week=0,
            max_consecutive_days=3, desired_shifts=2,
            preferred_shift_types=["morning"],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={},
        ),
        # 4. רן — junior, fully flexible
        EmployeeData(
            id="emp_ran", name="רן", role="junior",
            max_hours_per_week=48, min_hours_per_week=24,
            max_consecutive_days=6, desired_shifts=5,
            preferred_shift_types=[],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={},
        ),
        # 5. נועה — trainee, mornings only (preference, not hard)
        EmployeeData(
            id="emp_noa", name="נועה", role="trainee",
            max_hours_per_week=32, min_hours_per_week=16,
            max_consecutive_days=5, desired_shifts=4,
            preferred_shift_types=["morning"],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={0: ["morning"], 1: ["morning"], 2: ["morning"],
                                   3: ["morning"], 4: ["morning"], 5: ["morning"]},
        ),
        # 6. אבי — junior, hard block on Wednesday
        EmployeeData(
            id="emp_avi", name="אבי", role="junior",
            max_hours_per_week=40, min_hours_per_week=16,
            max_consecutive_days=4, desired_shifts=4,
            preferred_shift_types=["evening"],
            hard_blocked_dates={wed}, soft_blocked_dates=set(),
            day_type_preferences={},
        ),
        # 7. טל — manager, very flexible, many hours
        EmployeeData(
            id="emp_tal", name="טל", role="manager",
            max_hours_per_week=56, min_hours_per_week=32,
            max_consecutive_days=6, desired_shifts=6,
            preferred_shift_types=[],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={},
        ),
        # 8. גל — junior, soft block Fri, prefers few shifts
        EmployeeData(
            id="emp_gal", name="גל", role="junior",
            max_hours_per_week=24, min_hours_per_week=0,
            max_consecutive_days=3, desired_shifts=2,
            preferred_shift_types=["morning"],
            hard_blocked_dates=set(), soft_blocked_dates={fri},
            day_type_preferences={},
        ),
    ]

# ── Run simulation ─────────────────────────────────────────────────────────────
def run_simulation(label, employees, slots, scenario_note=""):
    print(f"\n{'='*60}")
    print(f"  {label}")
    if scenario_note:
        print(f"  {scenario_note}")
    print(f"{'='*60}")

    scheduler = ShiftScheduler(
        employees=employees,
        shift_slots=slots,
        week_start=WEEK_START,
        fairness_history={},
    )
    result = scheduler.build_and_solve(time_limit=5)

    print(f"\nStatus:    {result.solver_status}")
    print(f"Score:     {result.score}/100")
    print(f"Coverage:  {result.coverage_percent}%")
    print(f"Conflicts: {len(result.conflicts)}")
    print(f"Assignments: {len(result.assignments)}")

    # Per-employee breakdown
    print("\n--- Per-employee ---")
    emp_map = {e.id: e for e in employees}
    counts = {e.id: [] for e in employees}
    for a in result.assignments:
        counts[a.employee_id].append(a)
    for emp in employees:
        asgns = counts[emp.id]
        hours = sum(
            next(s.duration_hours for s in slots if s.id == a.shift_slot_id)
            for a in asgns
        )
        types = [next(s.shift_type for s in slots if s.id == a.shift_slot_id) for a in asgns]
        type_str = ", ".join(sorted(set(types))) if types else "—"
        print(f"  {emp.name:8s} ({emp.role:8s}): {len(asgns)} משמרות, {hours:.0f}h, סוגים: {type_str}")

    # Preference satisfaction
    print("\n--- העדפות יומיות ---")
    for emp in employees:
        if not emp.day_type_preferences:
            continue
        violations = []
        for a in counts[emp.id]:
            slot = next(s for s in slots if s.id == a.shift_slot_id)
            day_prefs = emp.day_type_preferences.get(slot.day_index)
            if day_prefs and slot.shift_type not in day_prefs:
                violations.append(f"יום {slot.day_index} ({slot.shift_type} במקום {day_prefs})")
        status = f"✗ הפרות: {violations}" if violations else "✓ כל ההעדפות נשמרו"
        print(f"  {emp.name}: {status}")

    # Conflicts
    if result.conflicts:
        print("\n--- קונפליקטים ---")
        for c in result.conflicts[:5]:
            print(f"  [{c['severity']}] {c['description']}")

    return result


if __name__ == "__main__":
    slots = make_slots()
    employees = make_employees()

    # ── Scenario 1: Base ───────────────────────────────────────────────────────
    r1 = run_simulation("תרחיש 1: בסיס — 8 עובדים, אילוצים שונים", employees, slots)

    # ── Scenario 2: Last-minute cancellation (אבי מבטל גם ראשון) ──────────────
    import copy
    emp2 = copy.deepcopy(employees)
    sun = WEEK_START.isoformat()
    for e in emp2:
        if e.id == "emp_avi":
            e.hard_blocked_dates.add(sun)
    run_simulation(
        "תרחיש 2: ביטול ברגע אחרון",
        emp2, slots,
        "אבי מוסיף חסימה קשה ביום ראשון בנוסף לרביעי"
    )

    # ── Scenario 3: New employee joins ────────────────────────────────────────
    emp3 = list(employees) + [
        EmployeeData(
            id="emp_new", name="חדש", role="junior",
            max_hours_per_week=32, min_hours_per_week=8,
            max_consecutive_days=5, desired_shifts=3,
            preferred_shift_types=["morning"],
            hard_blocked_dates=set(), soft_blocked_dates=set(),
            day_type_preferences={},
        )
    ]
    run_simulation("תרחיש 3: עובד חדש נכנס", emp3, slots,
                   "עובד חדש (junior, בוקר) מצטרף באמצע השבוע")

    # ── Scenario 4: Sudden availability change (דינה חוסמת גם Sun/Mon) ────────
    emp4 = copy.deepcopy(employees)
    mon = (WEEK_START + timedelta(days=1)).isoformat()
    for e in emp4:
        if e.id == "emp_dina":
            e.hard_blocked_dates.update({sun, mon})
    run_simulation(
        "תרחיש 4: שינוי זמינות פתאומי",
        emp4, slots,
        "דינה (בכירה) חוסמת ראשון ושני — מה קורה לכיסוי הבכיר?"
    )

    # ── Scenario 5: Minimal staff — only 4 employees ──────────────────────────
    run_simulation(
        "תרחיש 5: צוות מינימלי — 4 עובדים בלבד",
        employees[:4], slots,
        "בודק עומס יתר וכיסוי חסר עם 4 עובדים"
    )

    print("\n" + "="*60)
    print("  הסימולציה הסתיימה")
    print("="*60 + "\n")
