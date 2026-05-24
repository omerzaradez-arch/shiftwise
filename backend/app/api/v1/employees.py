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
    # Password is OPTIONAL. Employees interact only via the WhatsApp bot and
    # don't need a login. Set one only if you're creating another manager.
    password: str | None = None


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

    # Only managers/owners need a password. Employees interact via WhatsApp
    # and can never log in (enforced in /auth/login).
    is_manager_role = req.role in ("manager", "owner", "super_admin")
    if is_manager_role:
        if not req.password or len(req.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="עבור תפקיד ניהולי חובה להגדיר סיסמה (לפחות 8 תווים)",
            )
        hashed = hash_password(req.password)
    else:
        # Generate a random hash that nobody can ever guess. Employees can't
        # log in anyway (manager-only login), so this is just to satisfy the
        # non-nullable column.
        import secrets
        hashed = hash_password(secrets.token_urlsafe(32))

    emp = Employee(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=req.name,
        phone=req.phone,
        email=req.email,
        hashed_password=hashed,
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

    from datetime import datetime, timezone
    emp.is_active = False
    emp.tokens_invalidated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "deactivated"}


@router.get("/export-org-data")
async def export_org_data(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR / חוק הגנת הפרטיות: full data export for the caller's organization.

    Returns a ZIP file with CSVs for employees, schedules, shifts, attendance,
    availability submissions, and swap requests. Owner/super_admin only.
    """
    if current_user.role not in ("owner", "super_admin"):
        raise HTTPException(status_code=403, detail="רק בעל החשבון יכול לייצא נתוני ארגון")

    from fastapi.responses import Response
    from io import BytesIO, StringIO
    from zipfile import ZipFile, ZIP_DEFLATED
    import csv
    from datetime import datetime, timezone
    from app.models import ScheduleWeek, ScheduledShift, Attendance, Organization
    from app.models.availability import AvailabilitySubmission, UnavailabilitySlot
    from app.models.swap_request import SwapRequest

    org_id = current_user.org_id

    def rows_to_csv(rows: list[dict], headers: list[str]) -> str:
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        return buf.getvalue()

    async def fetch(model, **filters):
        q = select(model)
        for k, v in filters.items():
            q = q.where(getattr(model, k) == v)
        result = await db.execute(q)
        return result.scalars().all()

    # Organization
    org = await db.get(Organization, org_id)
    org_csv = rows_to_csv(
        [{"id": org.id, "name": org.name, "plan": org.plan,
          "created_at": org.created_at.isoformat() if org.created_at else "",
          "privacy_accepted_at": org.privacy_accepted_at.isoformat() if org.privacy_accepted_at else ""}],
        ["id", "name", "plan", "created_at", "privacy_accepted_at"],
    )

    # Employees
    employees = await fetch(Employee, org_id=org_id)
    employees_csv = rows_to_csv(
        [{
            "id": e.id, "name": e.name, "phone": e.phone, "email": e.email or "",
            "role": e.role, "employment_type": e.employment_type,
            "max_hours_per_week": e.max_hours_per_week,
            "hourly_rate": e.hourly_rate or "",
            "is_active": e.is_active,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        } for e in employees],
        ["id", "name", "phone", "email", "role", "employment_type",
         "max_hours_per_week", "hourly_rate", "is_active", "created_at"],
    )

    employee_ids = {e.id for e in employees}

    # Schedule weeks
    weeks = await fetch(ScheduleWeek, org_id=org_id)
    weeks_csv = rows_to_csv(
        [{"id": w.id, "week_start": w.week_start.isoformat(),
          "status": getattr(w, "status", ""),
          "created_at": w.created_at.isoformat() if getattr(w, "created_at", None) else ""}
         for w in weeks],
        ["id", "week_start", "status", "created_at"],
    )
    week_ids = {w.id for w in weeks}

    # Scheduled shifts (filter via week_id ∈ this org's weeks)
    shifts_q = await db.execute(select(ScheduledShift).where(ScheduledShift.week_id.in_(week_ids or {""})))
    shifts = shifts_q.scalars().all()
    shifts_csv = rows_to_csv(
        [{
            "id": s.id, "week_id": s.week_id, "employee_id": s.employee_id,
            "date": s.date.isoformat() if s.date else "",
            "start_time": s.start_time.isoformat() if s.start_time else "",
            "end_time": s.end_time.isoformat() if s.end_time else "",
            "shift_type": s.shift_type, "status": s.status,
        } for s in shifts],
        ["id", "week_id", "employee_id", "date", "start_time", "end_time", "shift_type", "status"],
    )

    # Attendance (filter via employee_id ∈ this org)
    att_q = await db.execute(select(Attendance).where(Attendance.employee_id.in_(employee_ids or {""})))
    attendance = att_q.scalars().all()
    attendance_csv = rows_to_csv(
        [{
            "id": a.id, "employee_id": a.employee_id,
            "shift_id": getattr(a, "shift_id", ""),
            "checked_in_at": a.checked_in_at.isoformat() if getattr(a, "checked_in_at", None) else "",
            "checked_out_at": a.checked_out_at.isoformat() if getattr(a, "checked_out_at", None) else "",
        } for a in attendance],
        ["id", "employee_id", "shift_id", "checked_in_at", "checked_out_at"],
    )

    # Availability submissions
    av_q = await db.execute(select(AvailabilitySubmission).where(AvailabilitySubmission.employee_id.in_(employee_ids or {""})))
    av_subs = av_q.scalars().all()
    av_csv = rows_to_csv(
        [{
            "id": s.id, "employee_id": s.employee_id,
            "week_id": getattr(s, "week_id", ""),
            "submitted_at": s.submitted_at.isoformat() if getattr(s, "submitted_at", None) else "",
        } for s in av_subs],
        ["id", "employee_id", "week_id", "submitted_at"],
    )

    # Swap requests
    sw_q = await db.execute(select(SwapRequest).where(SwapRequest.requester_id.in_(employee_ids or {""})))
    swaps = sw_q.scalars().all()
    swaps_csv = rows_to_csv(
        [{
            "id": s.id, "requester_id": s.requester_id,
            "shift_id": getattr(s, "shift_id", ""),
            "status": s.status,
            "created_at": s.created_at.isoformat() if getattr(s, "created_at", None) else "",
        } for s in swaps],
        ["id", "requester_id", "shift_id", "status", "created_at"],
    )

    # Build the ZIP
    zip_buf = BytesIO()
    with ZipFile(zip_buf, "w", ZIP_DEFLATED) as z:
        z.writestr("organization.csv", org_csv)
        z.writestr("employees.csv", employees_csv)
        z.writestr("schedule_weeks.csv", weeks_csv)
        z.writestr("scheduled_shifts.csv", shifts_csv)
        z.writestr("attendance.csv", attendance_csv)
        z.writestr("availability_submissions.csv", av_csv)
        z.writestr("swap_requests.csv", swaps_csv)
        z.writestr("README.txt", (
            f"ShiftWise data export\n"
            f"Organization: {org.name}\n"
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
            f"Requested by: {current_user.name} ({current_user.phone})\n\n"
            f"Files in this archive:\n"
            f"  organization.csv             — organization details\n"
            f"  employees.csv                — all employees\n"
            f"  schedule_weeks.csv           — weekly schedules\n"
            f"  scheduled_shifts.csv         — individual shift assignments\n"
            f"  attendance.csv               — check-in/out records\n"
            f"  availability_submissions.csv — weekly availability submitted\n"
            f"  swap_requests.csv            — shift swap requests\n"
        ))
    zip_buf.seek(0)

    filename = f"shiftwise_export_{org.name}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{employee_id}/revoke-tokens")
async def revoke_tokens(
    employee_id: str,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-logout an employee from every device without deactivating them.

    Useful when you suspect a stolen session, or as a step before a password
    reset. The employee can keep working — they'll just need to log in again.
    """
    if current_user.role not in ("manager", "owner", "super_admin"):
        raise HTTPException(status_code=403)

    emp = await db.get(Employee, employee_id)
    if not emp or emp.org_id != current_user.org_id:
        raise HTTPException(status_code=404)

    from datetime import datetime, timezone
    emp.tokens_invalidated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "tokens_revoked", "invalidated_at": emp.tokens_invalidated_at.isoformat()}
