from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import jwt, JWTError

from app.database import get_db
from app.models import Employee
from app.config import settings
from app.security import verify_password

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {**data, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        emp_id: str = payload.get("sub")
        if not emp_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    emp = await db.get(Employee, emp_id)
    if not emp or not emp.is_active:
        raise credentials_exc
    return emp


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee).where(Employee.phone == data.phone)
    )
    emp = result.scalar_one_or_none()

    if not emp or not verify_password(data.password, emp.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="פרטי התחברות שגויים",
        )

    token = create_access_token({"sub": emp.id, "org_id": emp.org_id})

    # Load org name
    from app.models import Organization
    org = await db.get(Organization, emp.org_id)

    return TokenResponse(
        access_token=token,
        user={
            "id": emp.id,
            "name": emp.name,
            "phone": emp.phone,
            "email": emp.email,
            "role": emp.role,
            "org_id": emp.org_id,
            "org_name": org.name if org else "",
        },
    )


@router.get("/me")
async def get_me(current_user: Employee = Depends(get_current_user)):
    from app.models import Organization
    return {
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "org_id": current_user.org_id,
    }


@router.post("/logout")
async def logout():
    return {"ok": True}


class SetupRequest(BaseModel):
    org_name: str
    name: str
    phone: str
    password: str


@router.post("/setup")
async def setup(data: SetupRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.models import Organization
    from app.security import hash_password
    import uuid
    count = await db.execute(select(func.count()).select_from(Employee))
    if count.scalar() > 0:
        raise HTTPException(status_code=403, detail="Setup already done")
    org = Organization(id=str(uuid.uuid4()), name=data.org_name)
    db.add(org)
    await db.flush()
    emp = Employee(
        id=str(uuid.uuid4()),
        org_id=org.id,
        name=data.name,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role="manager",
        is_active=True,
    )
    db.add(emp)
    await db.commit()
    return {"ok": True, "org_id": org.id}


class RegisterRequest(BaseModel):
    org_name: str
    name: str
    phone: str
    password: str
    email: str = ""
    verification_code: str = ""


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from app.models import Organization, PendingRegistration
    from app.security import hash_password
    from datetime import datetime, timezone
    import uuid, os

    # Verify the registration code
    if not data.verification_code:
        raise HTTPException(status_code=400, detail="חסר קוד אימות. בקש גישה תחילה.")

    # Find pending registration by phone + code
    clean_phone = data.phone.replace("-", "").replace(" ", "")
    pending_q = await db.execute(
        select(PendingRegistration).where(
            PendingRegistration.verification_code == data.verification_code.strip(),
            PendingRegistration.status == "pending",
        )
    )
    pending = pending_q.scalar_one_or_none()
    if not pending:
        raise HTTPException(status_code=400, detail="קוד אימות שגוי או לא תקף")

    # Phone must match (so the same code can't be used by random people)
    pending_phone = pending.phone.replace("-", "").replace(" ", "")
    if pending_phone != clean_phone:
        raise HTTPException(status_code=400, detail="קוד האימות לא תואם למספר טלפון זה")

    # Check phone not already taken
    existing = await db.execute(select(Employee).where(Employee.phone == data.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="מספר הטלפון כבר רשום במערכת")

    # Create org
    org = Organization(id=str(uuid.uuid4()), name=data.org_name)
    db.add(org)
    await db.flush()

    # Create manager
    emp = Employee(
        id=str(uuid.uuid4()),
        org_id=org.id,
        name=data.name,
        phone=data.phone,
        email=data.email or None,
        hashed_password=hash_password(data.password),
        role="owner",
        is_active=True,
    )
    db.add(emp)

    # Mark code as used
    pending.status = "used"
    pending.used_at = datetime.now(timezone.utc)

    await db.commit()

    token = create_access_token({"sub": emp.id, "org_id": org.id})
    return TokenResponse(
        access_token=token,
        user={
            "id": emp.id,
            "name": emp.name,
            "phone": emp.phone,
            "email": emp.email,
            "role": emp.role,
            "org_id": org.id,
            "org_name": org.name,
        },
    )


class AccessRequestData(BaseModel):
    org_name: str
    contact_name: str
    phone: str
    email: str = ""
    notes: str = ""


@router.post("/request-access")
async def request_access(data: AccessRequestData, db: AsyncSession = Depends(get_db)):
    """Submit a registration request — admin gets a notification with the code."""
    from app.models import PendingRegistration
    from app.api.v1.whatsapp import send_whatsapp_to
    import random, os

    # Generate 6-digit code
    code = f"{random.randint(0, 999999):06d}"

    pending = PendingRegistration(
        org_name=data.org_name.strip(),
        contact_name=data.contact_name.strip(),
        phone=data.phone.strip(),
        email=(data.email or "").strip() or None,
        notes=(data.notes or "").strip() or None,
        verification_code=code,
        status="pending",
    )
    db.add(pending)
    await db.commit()

    # Notify admin via WhatsApp
    admin_phone = os.getenv("ADMIN_PHONE", "")
    if admin_phone:
        msg = (
            f"🔔 *בקשת גישה חדשה ל-ShiftWise*\n\n"
            f"🏢 עסק: *{data.org_name}*\n"
            f"👤 איש קשר: {data.contact_name}\n"
            f"📞 טלפון: {data.phone}\n"
            f"📧 אימייל: {data.email or '—'}\n"
            + (f"📝 הערות: {data.notes}\n" if data.notes else "")
            + f"\n🔑 *קוד אימות:* `{code}`\n\n"
            f"_מסור את הקוד לעסק כדי שיוכל להשלים את ההרשמה._"
        )
        try:
            await send_whatsapp_to(admin_phone, msg)
        except Exception as e:
            print(f"[request-access] failed to notify admin: {e}", flush=True)

    return {
        "ok": True,
        "message": "הבקשה התקבלה. ניצור איתך קשר עם קוד אימות בהקדם.",
    }


@router.get("/debug-admin-whatsapp")
async def debug_admin_whatsapp():
    """Debug endpoint — sends a test WhatsApp to ADMIN_PHONE and returns status."""
    import os
    from app.api.v1.whatsapp import send_whatsapp_to

    result = {
        "ADMIN_PHONE_set": bool(os.getenv("ADMIN_PHONE")),
        "ADMIN_PHONE_value": os.getenv("ADMIN_PHONE", "(not set)"),
        "TWILIO_ACCOUNT_SID_set": bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "TWILIO_AUTH_TOKEN_set": bool(os.getenv("TWILIO_AUTH_TOKEN")),
        "TWILIO_WHATSAPP_NUMBER": os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886 (default)"),
    }

    admin = os.getenv("ADMIN_PHONE", "")
    if not admin:
        result["error"] = "ADMIN_PHONE לא מוגדר ב-Railway Variables"
        return result

    try:
        ok = await send_whatsapp_to(admin, "🔔 *בדיקה מ-ShiftWise*\n\nאם קיבלת את ההודעה הזו — ה-WhatsApp עובד מצוין! 🎉")
        result["whatsapp_sent"] = ok
        if not ok:
            result["error"] = "Twilio החזיר שגיאה. בדוק את ה-Railway logs."
    except Exception as e:
        result["error"] = f"Exception: {e}"

    return result


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str


@router.post("/verify-code")
async def verify_code(data: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    """Check if a code is valid for a given phone (used to enable the password step)."""
    from app.models import PendingRegistration
    clean_phone = data.phone.replace("-", "").replace(" ", "")
    pending_q = await db.execute(
        select(PendingRegistration).where(
            PendingRegistration.verification_code == data.code.strip(),
            PendingRegistration.status == "pending",
        )
    )
    pending = pending_q.scalar_one_or_none()
    if not pending:
        raise HTTPException(status_code=400, detail="קוד אימות שגוי או לא תקף")
    pending_phone = pending.phone.replace("-", "").replace(" ", "")
    if pending_phone != clean_phone:
        raise HTTPException(status_code=400, detail="הקוד לא תואם למספר הטלפון")
    return {
        "ok": True,
        "org_name": pending.org_name,
        "contact_name": pending.contact_name,
        "email": pending.email or "",
    }
