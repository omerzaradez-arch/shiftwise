from datetime import date, timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import FairnessTracking, Employee, ScheduleWeek
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/fairness/{week_id}")
async def get_fairness(
    week_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    records = (await db.execute(
        select(FairnessTracking, Employee)
        .join(Employee, FairnessTracking.employee_id == Employee.id)
        .where(
            FairnessTracking.week_id == week_id,
            FairnessTracking.org_id == current_user.org_id,
        )
    )).all()

    return [
        {
            "employee_id": emp.id,
            "employee_name": emp.name,
            "total_hours": ft.total_hours,
            "weekend_shifts": ft.weekend_shifts,
            "evening_shifts": ft.evening_shifts,
            "morning_shifts": ft.morning_shifts,
        }
        for ft, emp in records
    ]


@router.get("/hours-distribution")
async def get_hours_distribution(
    weeks: int = 8,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    cutoff = date.today() - timedelta(weeks=weeks)

    results = (await db.execute(
        select(
            Employee.id,
            Employee.name,
            func.sum(FairnessTracking.total_hours).label("total_hours"),
            func.sum(FairnessTracking.weekend_shifts).label("weekend_shifts"),
            func.avg(FairnessTracking.total_hours).label("avg_weekly_hours"),
        )
        .join(Employee, FairnessTracking.employee_id == Employee.id)
        .join(ScheduleWeek, FairnessTracking.week_id == ScheduleWeek.id)
        .where(
            FairnessTracking.org_id == current_user.org_id,
            ScheduleWeek.week_start >= cutoff,
        )
        .group_by(Employee.id, Employee.name)
        .order_by(func.sum(FairnessTracking.total_hours).desc())
    )).all()

    return [
        {
            "employee_id": r.id,
            "employee_name": r.name,
            "total_hours": round(r.total_hours or 0, 1),
            "weekend_shifts": r.weekend_shifts or 0,
            "avg_weekly_hours": round(r.avg_weekly_hours or 0, 1),
        }
        for r in results
    ]


@router.get("/payroll-trend")
async def get_payroll_trend(
    months: int = 6,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly payroll cost and hours for the last N months."""
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    try:
        from app.models.attendance import Attendance
        from sqlalchemy import and_

        today = datetime.now(timezone.utc).date()
        result = []

        for i in range(months - 1, -1, -1):
            # Calculate month start/end
            month_date = date(today.year, today.month, 1)
            # Go back i months
            m = month_date.month - i
            y = month_date.year
            while m <= 0:
                m += 12
                y -= 1
            month_start = date(y, m, 1)
            if m == 12:
                month_end = date(y + 1, 1, 1)
            else:
                month_end = date(y, m + 1, 1)

            # Get all attendance for this org in this month
            rows = (await db.execute(
                select(Attendance, Employee)
                .join(Employee, Attendance.employee_id == Employee.id)
                .where(
                    and_(
                        Attendance.org_id == current_user.org_id,
                        Attendance.date >= month_start,
                        Attendance.date < month_end,
                        Attendance.check_out != None,
                    )
                )
            )).all()

            total_minutes = sum(r.Attendance.total_minutes or 0 for r in rows)
            total_hours = round(total_minutes / 60, 1)
            total_payroll = sum(
                round((r.Employee.hourly_rate or 0) * (r.Attendance.total_minutes or 0) / 60, 2)
                for r in rows
            )
            days_worked = len(set(r.Attendance.date for r in rows))

            month_names = ["ינו׳", "פבר׳", "מרץ", "אפר׳", "מאי", "יוני",
                           "יולי", "אוג׳", "ספט׳", "אוק׳", "נוב׳", "דצמ׳"]

            result.append({
                "month": f"{month_names[m - 1]} {y}",
                "month_num": m,
                "year": y,
                "total_hours": total_hours,
                "total_payroll": round(total_payroll, 0),
                "days_worked": days_worked,
                "shifts_count": len(rows),
            })

        return result
    except Exception:
        return []


@router.get("/attendance-stats")
async def get_attendance_stats(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-employee attendance stats for current month."""
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    try:
        from app.models.attendance import Attendance
        from sqlalchemy import and_

        today = datetime.now(timezone.utc).date()
        month_start = date(today.year, today.month, 1)
        month_end = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)

        rows = (await db.execute(
            select(Attendance, Employee)
            .join(Employee, Attendance.employee_id == Employee.id)
            .where(
                and_(
                    Attendance.org_id == current_user.org_id,
                    Attendance.date >= month_start,
                    Attendance.date < month_end,
                    Attendance.check_out != None,
                )
            )
        )).all()

        # Group by employee
        emp_data: dict = {}
        for row in rows:
            eid = row.Employee.id
            if eid not in emp_data:
                emp_data[eid] = {
                    "employee_id": eid,
                    "employee_name": row.Employee.name,
                    "days": 0,
                    "total_minutes": 0,
                    "invalid_location": 0,
                }
            emp_data[eid]["days"] += 1
            emp_data[eid]["total_minutes"] += row.Attendance.total_minutes or 0
            if not row.Attendance.is_valid_location:
                emp_data[eid]["invalid_location"] += 1

        result = []
        for emp in emp_data.values():
            total_hours = round(emp["total_minutes"] / 60, 1)
            avg_hours_per_day = round(total_hours / emp["days"], 1) if emp["days"] > 0 else 0
            result.append({
                **emp,
                "total_hours": total_hours,
                "avg_hours_per_day": avg_hours_per_day,
            })

        return sorted(result, key=lambda x: x["total_hours"], reverse=True)
    except Exception:
        return []
