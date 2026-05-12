from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import time
from typing import Optional

from app.database import get_db
from app.models import Employee, ShiftTemplate
from app.api.v1.auth import get_current_user

router = APIRouter()


class ShiftTemplateCreate(BaseModel):
    name: str
    shift_type: str = "morning"
    start_time: str
    end_time: str
    min_employees: int = 1
    max_employees: int = 10
    required_roles: dict = {}
    days_of_week: list = []


class ShiftTemplateUpdate(BaseModel):
    name: Optional[str] = None
    shift_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    required_roles: Optional[dict] = None
    days_of_week: Optional[list] = None
    is_active: Optional[bool] = None


def parse_time(t: str) -> time:
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


def template_to_dict(t: ShiftTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "shift_type": t.shift_type,
        "start_time": t.start_time.strftime("%H:%M"),
        "end_time": t.end_time.strftime("%H:%M"),
        "min_employees": t.min_employees,
        "max_employees": t.max_employees,
        "required_roles": t.required_roles,
        "days_of_week": t.days_of_week,
        "is_active": t.is_active,
        "duration_hours": t.duration_hours,
    }


@router.get("/")
async def list_templates(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShiftTemplate)
        .where(ShiftTemplate.org_id == current_user.org_id)
        .order_by(ShiftTemplate.start_time)
    )
    return [template_to_dict(t) for t in result.scalars().all()]


@router.post("/", status_code=201)
async def create_template(
    req: ShiftTemplateCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    template = ShiftTemplate(
        org_id=current_user.org_id,
        name=req.name,
        shift_type=req.shift_type,
        start_time=parse_time(req.start_time),
        end_time=parse_time(req.end_time),
        min_employees=req.min_employees,
        max_employees=req.max_employees,
        required_roles=req.required_roles,
        days_of_week=req.days_of_week,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template_to_dict(template)


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    req: ShiftTemplateUpdate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    template = await db.get(ShiftTemplate, template_id)
    if not template or template.org_id != current_user.org_id:
        raise HTTPException(status_code=404)

    if req.name is not None:
        template.name = req.name
    if req.shift_type is not None:
        template.shift_type = req.shift_type
    if req.start_time is not None:
        template.start_time = parse_time(req.start_time)
    if req.end_time is not None:
        template.end_time = parse_time(req.end_time)
    if req.min_employees is not None:
        template.min_employees = req.min_employees
    if req.max_employees is not None:
        template.max_employees = req.max_employees
    if req.required_roles is not None:
        template.required_roles = req.required_roles
    if req.days_of_week is not None:
        template.days_of_week = req.days_of_week
    if req.is_active is not None:
        template.is_active = req.is_active

    await db.commit()
    return template_to_dict(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    template = await db.get(ShiftTemplate, template_id)
    if not template or template.org_id != current_user.org_id:
        raise HTTPException(status_code=404)

    await db.delete(template)
    await db.commit()
