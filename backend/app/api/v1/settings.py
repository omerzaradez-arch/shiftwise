from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import Employee, Organization
from app.api.v1.auth import get_current_user

router = APIRouter()


class OrgSettings(BaseModel):
    org_name: str | None = None
    min_senior_per_shift: int | None = None
    min_staff_per_shift: int | None = None
    availability_deadline_day: int | None = None  # 0=Sun … 6=Sat
    publish_day: int | None = None
    notes: str | None = None
    operating_days: list | None = None  # [0..6] days open, 0=Sun 6=Sat
    onboarding_complete: bool | None = None


@router.get("/")
async def get_settings(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    org = await db.get(Organization, current_user.org_id)
    if not org:
        raise HTTPException(status_code=404)

    return {
        "org_name": org.name,
        "org_id": org.id,
        "plan": org.plan,
        "timezone": org.timezone,
        **org.settings,
    }


@router.patch("/")
async def update_settings(
    req: OrgSettings,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("owner", "super_admin", "manager"):
        raise HTTPException(status_code=403)

    org = await db.get(Organization, current_user.org_id)
    if not org:
        raise HTTPException(status_code=404)

    if req.org_name is not None:
        org.name = req.org_name

    settings = dict(org.settings or {})
    for field in ("min_senior_per_shift", "min_staff_per_shift",
                  "availability_deadline_day", "publish_day", "notes",
                  "operating_days", "onboarding_complete"):
        val = getattr(req, field)
        if val is not None:
            settings[field] = val
    org.settings = settings
    await db.commit()

    return {"status": "ok"}
