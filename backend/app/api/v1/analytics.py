from datetime import date, timedelta
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
