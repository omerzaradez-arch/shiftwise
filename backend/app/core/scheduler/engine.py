"""
ShiftWise Scheduling Engine
Uses Google OR-Tools CP-SAT solver for optimal shift assignment.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import logging

from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)


@dataclass
class EmployeeData:
    id: str
    name: str
    role: str  # senior | junior | trainee | manager
    max_hours_per_week: float
    min_hours_per_week: float
    max_consecutive_days: int
    desired_shifts: int
    preferred_shift_types: list[str]
    hard_blocked_dates: set[str]          # "yyyy-mm-dd"
    soft_blocked_dates: set[str]          # preferred not to work
    historical_weekend_shifts: int = 0    # last 8 weeks
    historical_evening_shifts: int = 0
    # per-day shift type preferences: {day_index -> [preferred types]}
    day_type_preferences: dict = field(default_factory=dict)


@dataclass
class ShiftSlot:
    id: str
    template_id: str
    date: str                    # "yyyy-mm-dd"
    day_index: int               # 0=Sun ... 6=Sat
    start_time: str
    end_time: str
    duration_hours: float
    shift_type: str              # morning | afternoon | evening | night
    min_employees: int
    max_employees: int
    required_roles: dict[str, int]   # {"senior": 1, "junior": 2}
    is_weekend: bool             # Fri/Sat/Sun


@dataclass
class Assignment:
    employee_id: str
    shift_slot_id: str
    date: str
    template_id: str


@dataclass
class ScheduleResult:
    assignments: list[Assignment]
    score: float
    coverage_percent: float
    conflicts: list[dict]
    solver_status: str
    solve_time_seconds: float
    metadata: dict = field(default_factory=dict)


class ShiftScheduler:
    def __init__(
        self,
        employees: list[EmployeeData],
        shift_slots: list[ShiftSlot],
        week_start: date,
        fairness_history: dict[str, dict] | None = None,
    ):
        self.employees = employees
        self.shift_slots = shift_slots
        self.week_start = week_start
        self.fairness_history = fairness_history or {}
        self.model = cp_model.CpModel()
        self.vars: dict[tuple[str, str], cp_model.IntVar] = {}

    def build_and_solve(self, time_limit: int = 30) -> ScheduleResult:
        import time as _time
        t0 = _time.time()

        self._create_variables()
        self._add_hard_constraints()
        objective = self._build_objective()
        self.model.minimize(objective)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_workers = 8
        solver.parameters.log_search_progress = False

        status = solver.solve(self.model)
        elapsed = _time.time() - t0

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        status_str = status_map.get(status, "UNKNOWN")
        logger.info(f"Solver finished: {status_str} in {elapsed:.2f}s")

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return self._extract_result(solver, status_str, elapsed)
        else:
            logger.warning("CP-SAT infeasible, falling back to greedy")
            return self._greedy_fallback(elapsed)

    def _create_variables(self):
        for emp in self.employees:
            for slot in self.shift_slots:
                self.vars[(emp.id, slot.id)] = self.model.new_bool_var(
                    f"e{emp.id[:8]}_s{slot.id[:8]}"
                )

    def _add_hard_constraints(self):
        # 1. Coverage: min/max employees per slot
        for slot in self.shift_slots:
            assigned = [self.vars[(emp.id, slot.id)] for emp in self.employees]
            self.model.add(sum(assigned) >= slot.min_employees)
            self.model.add(sum(assigned) <= slot.max_employees)

        # 2. One shift per employee per day
        slots_by_date: dict[str, list[ShiftSlot]] = {}
        for slot in self.shift_slots:
            slots_by_date.setdefault(slot.date, []).append(slot)

        for emp in self.employees:
            for day_slots in slots_by_date.values():
                daily = [self.vars[(emp.id, s.id)] for s in day_slots]
                self.model.add(sum(daily) <= 1)

        # 3. Hard unavailability blocks
        for emp in self.employees:
            for slot in self.shift_slots:
                if slot.date in emp.hard_blocked_dates:
                    self.model.add(self.vars[(emp.id, slot.id)] == 0)

        # Close-then-open is allowed (not ideal but permitted)

        # 5. At least one senior per slot
        senior_ids = {e.id for e in self.employees if e.role in ("senior", "manager")}
        for slot in self.shift_slots:
            if senior_ids:
                seniors = [self.vars[(e_id, slot.id)] for e_id in senior_ids]
                self.model.add(sum(seniors) >= 1)

        # 6. Required roles per slot
        for slot in self.shift_slots:
            for role, count in slot.required_roles.items():
                role_emps = [e for e in self.employees if e.role == role]
                if role_emps:
                    role_vars = [self.vars[(e.id, slot.id)] for e in role_emps]
                    self.model.add(sum(role_vars) >= count)

        # 7. Weekly hours limits
        for emp in self.employees:
            total_minutes = sum(
                self.vars[(emp.id, slot.id)] * int(slot.duration_hours * 60)
                for slot in self.shift_slots
            )
            self.model.add(total_minutes <= int(emp.max_hours_per_week * 60))
            self.model.add(total_minutes >= int(emp.min_hours_per_week * 60))

        # 8. Max consecutive working days
        dates_sorted = sorted(slots_by_date.keys())
        for emp in self.employees:
            max_consec = emp.max_consecutive_days
            for start_i in range(len(dates_sorted) - max_consec):
                window = dates_sorted[start_i: start_i + max_consec + 1]
                worked_days = []
                for d in window:
                    day_slots = slots_by_date.get(d, [])
                    if day_slots:
                        worked = self.model.new_bool_var(f"worked_{emp.id[:6]}_{d}")
                        self.model.add_max_equality(
                            worked, [self.vars[(emp.id, s.id)] for s in day_slots]
                        )
                        worked_days.append(worked)
                if len(worked_days) > max_consec:
                    self.model.add(sum(worked_days) <= max_consec)

    def _build_objective(self) -> cp_model.LinearExprT:
        penalties = []

        # Penalty: soft unavailability
        for emp in self.employees:
            for slot in self.shift_slots:
                if slot.date in emp.soft_blocked_dates:
                    penalties.append(self.vars[(emp.id, slot.id)] * 3)

        # Penalty: not meeting desired shift count
        for emp in self.employees:
            all_assigned = [self.vars[(emp.id, slot.id)] for slot in self.shift_slots]
            total = sum(all_assigned)
            over = self.model.new_int_var(0, 20, f"over_{emp.id[:6]}")
            under = self.model.new_int_var(0, 20, f"under_{emp.id[:6]}")
            self.model.add(total - emp.desired_shifts == over - under)
            penalties.append(over * 2)
            penalties.append(under * 2)

        # Penalty: shift type mismatch
        for emp in self.employees:
            if emp.preferred_shift_types:
                for slot in self.shift_slots:
                    if slot.shift_type not in emp.preferred_shift_types:
                        penalties.append(self.vars[(emp.id, slot.id)] * 1)

        # Penalty: weekend fairness (historical burden)
        weekend_slots = [s for s in self.shift_slots if s.is_weekend]
        for emp in self.employees:
            historical_burden = self.fairness_history.get(emp.id, {}).get(
                "weekend_shifts_per_week", 0
            )
            if historical_burden > 1.5:
                for slot in weekend_slots:
                    penalties.append(self.vars[(emp.id, slot.id)] * 5)

        # Reward: global shift type preferences met
        for emp in self.employees:
            for slot in self.shift_slots:
                if slot.shift_type in emp.preferred_shift_types:
                    penalties.append(self.vars[(emp.id, slot.id)] * -1)

        # Per-day shift type preferences (from WhatsApp availability)
        for emp in self.employees:
            for slot in self.shift_slots:
                day_prefs = emp.day_type_preferences.get(slot.day_index) or \
                            emp.day_type_preferences.get(str(slot.day_index))
                if not day_prefs:
                    continue
                if slot.shift_type not in day_prefs:
                    penalties.append(self.vars[(emp.id, slot.id)] * 500)
                else:
                    penalties.append(self.vars[(emp.id, slot.id)] * -50)

        return sum(penalties) if penalties else cp_model.LinearExpr.sum([])

    def _extract_result(
        self, solver: cp_model.CpSolver, status: str, elapsed: float
    ) -> ScheduleResult:
        assignments = []
        for emp in self.employees:
            for slot in self.shift_slots:
                if solver.value(self.vars[(emp.id, slot.id)]):
                    assignments.append(
                        Assignment(
                            employee_id=emp.id,
                            shift_slot_id=slot.id,
                            date=slot.date,
                            template_id=slot.template_id,
                        )
                    )

        score = self._calculate_score(assignments)
        coverage = self._calculate_coverage(assignments)
        conflicts = self._detect_conflicts(assignments)

        return ScheduleResult(
            assignments=assignments,
            score=score,
            coverage_percent=coverage,
            conflicts=conflicts,
            solver_status=status,
            solve_time_seconds=elapsed,
            metadata={
                "objective_value": solver.objective_value,
                "num_assignments": len(assignments),
            },
        )

    def _calculate_score(self, assignments: list[Assignment]) -> float:
        coverage = self._calculate_coverage(assignments)
        fairness = self._calculate_fairness_score(assignments)
        conflicts = len(self._detect_conflicts(assignments))

        coverage_score = min(coverage / 100 * 30, 30)
        fairness_score = fairness * 25
        preference_score = self._preference_score(assignments) * 25
        conflict_penalty = min(conflicts * 5, 20)

        return round(coverage_score + fairness_score + preference_score - conflict_penalty + 20, 1)

    def _calculate_coverage(self, assignments: list[Assignment]) -> float:
        assigned_slots = {a.shift_slot_id for a in assignments}
        covered = 0
        total = 0
        for slot in self.shift_slots:
            slot_assigned = sum(
                1 for a in assignments if a.shift_slot_id == slot.id
            )
            total += slot.min_employees
            covered += min(slot_assigned, slot.min_employees)
        return round((covered / total * 100) if total > 0 else 100, 1)

    def _calculate_fairness_score(self, assignments: list[Assignment]) -> float:
        from statistics import stdev
        counts = {}
        for emp in self.employees:
            counts[emp.id] = sum(1 for a in assignments if a.employee_id == emp.id)
        if len(counts) < 2:
            return 1.0
        values = list(counts.values())
        if max(values) == 0:
            return 1.0
        sd = stdev(values) if len(values) > 1 else 0
        normalized_sd = sd / (max(values) or 1)
        return round(max(0, 1 - normalized_sd), 2)

    def _preference_score(self, assignments: list[Assignment]) -> float:
        met = 0
        total = 0
        emp_map = {e.id: e for e in self.employees}
        slot_map = {s.id: s for s in self.shift_slots}
        for a in assignments:
            emp = emp_map.get(a.employee_id)
            slot = slot_map.get(a.shift_slot_id)
            if emp and slot and emp.preferred_shift_types:
                total += 1
                if slot.shift_type in emp.preferred_shift_types:
                    met += 1
        return met / total if total > 0 else 1.0

    def _detect_conflicts(self, assignments: list[Assignment]) -> list[dict]:
        conflicts = []

        # Close-open conflicts
        by_emp_date: dict[tuple[str, str], list[str]] = {}
        slot_map = {s.id: s for s in self.shift_slots}
        for a in assignments:
            key = (a.employee_id, a.date)
            by_emp_date.setdefault(key, []).append(a.shift_slot_id)

        emp_map = {e.id: e for e in self.employees}
        for (emp_id, d), slot_ids in by_emp_date.items():
            for sid in slot_ids:
                slot = slot_map.get(sid)
                if slot and slot.shift_type in ("evening", "night"):
                    next_day = str(date.fromisoformat(d) + timedelta(days=1))
                    next_key = (emp_id, next_day)
                    if next_key in by_emp_date:
                        for next_sid in by_emp_date[next_key]:
                            next_slot = slot_map.get(next_sid)
                            if next_slot and next_slot.shift_type == "morning":
                                conflicts.append({
                                    "type": "close_open",
                                    "severity": "high",
                                    "employee_id": emp_id,
                                    "date": d,
                                    "description": f"{emp_map.get(emp_id, type('', (), {'name': emp_id})()).name} — סגירה ב-{d} ופתיחה ב-{next_day}",
                                    "suggestion": "החלף עם עובד אחר",
                                })

        # Under-coverage
        for slot in self.shift_slots:
            count = sum(1 for a in assignments if a.shift_slot_id == slot.id)
            if count < slot.min_employees:
                conflicts.append({
                    "type": "under_coverage",
                    "severity": "high",
                    "date": slot.date,
                    "description": f"משמרת {slot.shift_type} ב-{slot.date}: {count}/{slot.min_employees} עובדים",
                    "suggestion": "הוסף עובד ידנית או שנה את דרישת המינימום",
                })

        return conflicts

    def _greedy_fallback(self, elapsed: float) -> ScheduleResult:
        """Simple greedy: fill each slot with available employees."""
        assignments = []
        emp_shift_count: dict[str, int] = {e.id: 0 for e in self.employees}
        emp_hours: dict[str, float] = {e.id: 0.0 for e in self.employees}
        emp_dates_worked: dict[str, set[str]] = {e.id: set() for e in self.employees}

        for slot in sorted(self.shift_slots, key=lambda s: (s.date, s.min_employees), reverse=True):
            needed = slot.min_employees
            assigned_count = 0

            candidates = [
                e for e in self.employees
                if slot.date not in e.hard_blocked_dates
                and slot.date not in emp_dates_worked[e.id]
                and emp_hours[e.id] + slot.duration_hours <= e.max_hours_per_week
            ]

            # Prioritize: seniors first, then preference match, then fewest shifts
            def _day_pref_penalty(e):
                day_prefs = e.day_type_preferences.get(slot.day_index) or \
                            e.day_type_preferences.get(str(slot.day_index))
                if day_prefs:
                    return 0 if slot.shift_type in day_prefs else 1
                return 0

            candidates.sort(key=lambda e: (
                0 if e.role in ("senior", "manager") else 1,
                _day_pref_penalty(e),
                emp_shift_count[e.id],
            ))

            for emp in candidates:
                if assigned_count >= needed:
                    break
                assignments.append(Assignment(
                    employee_id=emp.id,
                    shift_slot_id=slot.id,
                    date=slot.date,
                    template_id=slot.template_id,
                ))
                emp_shift_count[emp.id] += 1
                emp_hours[emp.id] += slot.duration_hours
                emp_dates_worked[emp.id].add(slot.date)
                assigned_count += 1

        score = self._calculate_score(assignments)
        coverage = self._calculate_coverage(assignments)
        conflicts = self._detect_conflicts(assignments)

        return ScheduleResult(
            assignments=assignments,
            score=score,
            coverage_percent=coverage,
            conflicts=conflicts,
            solver_status="GREEDY_FALLBACK",
            solve_time_seconds=elapsed,
        )
