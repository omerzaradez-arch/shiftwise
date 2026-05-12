from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import Employee
from app.api.v1.auth import get_current_user
from app.security import hash_password
import uuid

router = APIRouter()


class CreateEmployeeRequest(BaseModel):
    name: str
    phone: str
    email: str | None = None
    role: str = "junior"
    employment_type: str = "part_time"
    max_hours_per_week: int = 40
    min_hours_per_week: int = 0
    max_consecutive_days: int = 5
    skills: list[str] = []
    hourly_rate: float | None = None
    password: str


@router.get("/")
async def list_employees(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    emps = (await db.execute(
        select(Employee).where(
            Employee.org_id == current_user.org_id,
            Employee.is_active == True,
        ).order_by(Employee.name)
    )).scalars().all()

    return [
        {
            "id": e.id,
            "name": e.name,
            "phone": e.phone,
            "email": e.email,
            "role": e.role,
            "employment_type": e.employment_type,
            "max_hours_per_week": e.max_hours_per_week,
            "min_hours_per_week": e.min_hours_per_week,
            "skills": e.skills,
            "hourly_rate": e.hourly_rate,
        }
        for e in emps
    ]


@router.post("/")
async def create_employee(
    req: CreateEmployeeRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    emp = Employee(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=req.name,
        phone=req.phone,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role,
        employment_type=req.employment_type,
        max_hours_per_week=req.max_hours_per_week,
        min_hours_per_week=req.min_hours_per_week,
        max_consecutive_days=req.max_consecutive_days,
        skills=req.skills,
        hourly_rate=req.hourly_rate,
    )
    db.add(emp)
    await db.commit()
    return {"id": emp.id, "name": emp.name}


class UpdateEmployeeRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    role: str | None = None
    employment_type: str | None = None
    max_hours_per_week: int | None = None
    min_hours_per_week: int | None = None
    hourly_rate: float | None = None


@router.patch("/{employee_id}")
async def update_employee(
    employee_id: str,
    req: UpdateEmployeeRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    emp = await db.get(Employee, employee_id)
    if not emp or emp.org_id != current_user.org_id:
        raise HTTPException(status_code=404)

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(emp, field, value)
    await db.commit()
    return {"id": emp.id, "name": emp.name}


@router.delete("/{employee_id}")
async def deactivate_employee(
    employee_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("owner", "super_admin"):
        raise HTTPException(status_code=403)

    emp = await db.get(Employee, employee_id)
    if not emp or emp.org_id != current_user.org_id:
        raise HTTPException(status_code=404)

    emp.is_active = False
    await db.commit()
    return {"status": "deactivated"}
