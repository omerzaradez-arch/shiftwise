from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from jose import jwt, JWTError

from app.database import get_db
from app.models import Employee
from app.config import settings
from app.security import verify_password
from app.limiter import limiter

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"הסיסמה חייבת להיות לפחות {MIN_PASSWORD_LENGTH} תווים")
    if value.isdigit():
        raise ValueError("הסיסמה לא יכולה להיות מספרים בלבד")
    return value


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def create_access_token(data: dict) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {**data, "iat": now, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_checkin_token(shift_id: str, employee_id: str, hours: int = 6) -> str:
    """Short-lived signed token for one-tap GPS check-in via web link."""
    expire = datetime.now(timezone.utc) + timedelta(hours=hours)
    return jwt.encode(
        {"sid": shift_id, "eid": employee_id, "exp": expire, "kind": "checkin"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def verify_checkin_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("kind") != "checkin":
            return None
        return payload
    except JWTError:
        return None


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
        token_iat = payload.get("iat")
        if not emp_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    emp = await db.get(Employee, emp_id)
    if not emp or not emp.is_active:
        raise credentials_exc

    # Reject tokens issued before the user's last revocation moment.
    if emp.tokens_invalidated_at and token_iat is not None:
        from datetime import datetime as _dt, timezone as _tz
        iat_dt = _dt.fromtimestamp(token_iat, tz=_tz.utc)
        if iat_dt < emp.tokens_invalidated_at:
            raise credentials_exc

    return emp


MANAGER_ROLES = ("owner", "manager", "super_admin")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee).where(Employee.phone == data.phone)
    )
    emp = result.scalar_one_or_none()

    if not emp or not verify_password(data.password, emp.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="פרטי התחברות שגויים",
        )

    # Employees interact via WhatsApp only — block their login.
    if emp.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="המערכת מיועדת למנהלים בלבד. עובדים מקבלים שירות ב-WhatsApp.",
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


@router.post("/logout-everywhere")
async def logout_everywhere(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate every JWT issued before now for the current user."""
    current_user.tokens_invalidated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "invalidated_at": current_user.tokens_invalidated_at.isoformat()}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the logged-in user's password.

    Verifies the current password, then sets the new one and invalidates all
    existing sessions so the user must log in again with the new password.
    """
    from app.security import hash_password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="הסיסמה הנוכחית שגויה")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="הסיסמה החדשה חייבת להיות שונה מהנוכחית")
    current_user.hashed_password = hash_password(data.new_password)
    current_user.tokens_invalidated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "message": "הסיסמה הוחלפה בהצלחה. אנא היכנס מחדש."}


class SetupRequest(BaseModel):
    org_name: str
    name: str
    phone: str
    password: str
    privacy_accepted: bool = False

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("privacy_accepted")
    @classmethod
    def _must_accept_privacy(cls, v: bool) -> bool:
        if not v:
            raise ValueError("חובה לאשר את מדיניות הפרטיות לפני יצירת החשבון")
        return v


@router.post("/setup")
async def setup(data: SetupRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.models import Organization
    from app.security import hash_password
    import uuid
    count = await db.execute(select(func.count()).select_from(Employee))
    if count.scalar() > 0:
        raise HTTPException(status_code=403, detail="Setup already done")
    now = datetime.now(timezone.utc)
    org = Organization(id=str(uuid.uuid4()), name=data.org_name, privacy_accepted_at=now)
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
        privacy_accepted_at=now,
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
    privacy_accepted: bool = False

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("privacy_accepted")
    @classmethod
    def _must_accept_privacy(cls, v: bool) -> bool:
        if not v:
            raise ValueError("חובה לאשר את מדיניות הפרטיות לפני יצירת החשבון")
        return v


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
    now = datetime.now(timezone.utc)
    org = Organization(id=str(uuid.uuid4()), name=data.org_name, privacy_accepted_at=now)
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
        privacy_accepted_at=now,
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


class ForgotPasswordRequest(BaseModel):
    phone: str


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new random password and send it to the manager.

    Email is the delivery channel whenever we have an address for them — a
    password sitting in a WhatsApp thread is readable by anyone who picks up
    the phone, and stays there forever. WhatsApp then only carries a notice
    with no secret in it. Without an address on file we fall back to sending
    the password over WhatsApp, as before.

    Always returns 200 — never leaks whether the phone exists in the system
    (prevents user enumeration). Rate limited to 3 per hour per IP.
    """
    from app.security import hash_password
    from app.core import wa, mail
    import secrets, string

    clean_phone = data.phone.replace("-", "").replace(" ", "")
    result = await db.execute(
        select(Employee).where(Employee.phone == clean_phone, Employee.is_active == True)
    )
    emp = result.scalar_one_or_none()

    # Same response whether the phone exists or not.
    generic_response = {
        "ok": True,
        "message": "אם המספר רשום במערכת ושייך למנהל, סיסמה חדשה נשלחה במייל או ב-WhatsApp.",
    }

    if not emp or emp.role not in MANAGER_ROLES:
        return generic_response

    # Build an easy-to-type 10-char password (no ambiguous chars 0/O/1/l/I).
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    new_password = "".join(secrets.choice(alphabet) for _ in range(10))
    # Ensure it passes our own validator (mixed types, length 10).
    _validate_password_strength(new_password)

    emp.hashed_password = hash_password(new_password)
    # Force-logout any existing sessions immediately.
    emp.tokens_invalidated_at = datetime.now(timezone.utc)
    await db.commit()

    emailed = False
    if emp.email and mail.is_configured():
        try:
            emailed = await mail.send_password_reset(emp.email, emp.name, new_password)
        except Exception as e:
            print(f"[forgot-password] email exception: {e}", flush=True)

    try:
        if emailed:
            # Secret already delivered — WhatsApp just points them at the inbox.
            masked = mail.mask_email(emp.email)
            notice = (
                "🔐 *איפוס סיסמה ל-ShiftWise*\n\n"
                f"שלום {emp.name},\n"
                f"שלחנו סיסמה חדשה לכתובת {masked}.\n\n"
                "אם לא ביקשת את האיפוס — מישהו ניסה להיכנס לחשבון שלך. פנה אלינו מיד."
            )
            await wa.notify_password_reset(emp.phone, emp.name, masked, fallback_body=notice)
        else:
            if emp.email:
                print("[forgot-password] email failed — falling back to WhatsApp", flush=True)
            message = (
                "🔐 *איפוס סיסמה ל-ShiftWise*\n\n"
                f"שלום {emp.name},\n"
                "ביקשת לאפס את הסיסמה למערכת ShiftWise.\n\n"
                f"הסיסמה החדשה שלך: *{new_password}*\n\n"
                "מומלץ להחליף אותה לסיסמה משלך בהגדרות המערכת אחרי הכניסה.\n\n"
                "אם לא ביקשת את האיפוס — מישהו ניסה להיכנס לחשבון שלך. "
                "פנה אלינו מיד."
            )
            sent = await wa.send_text(emp.phone, message)
            if not sent:
                print(f"[forgot-password] WhatsApp send returned False for {emp.phone}", flush=True)
    except Exception as e:
        print(f"[forgot-password] WhatsApp exception: {e}", flush=True)

    return generic_response


class AccessRequestData(BaseModel):
    org_name: str
    contact_name: str
    phone: str
    email: str = ""
    notes: str = ""


@router.post("/request-access")
@limiter.limit("3/hour")
async def request_access(data: AccessRequestData, request: Request, db: AsyncSession = Depends(get_db)):
    """Submit a registration request — admin gets a notification with the code."""
    from app.models import PendingRegistration
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
            from app.core import wa
            await wa.notify_admin_new_registration(
                admin_phone, data.org_name, data.contact_name, data.phone, code,
                fallback_body=msg,
            )
        except Exception as e:
            print(f"[request-access] failed to notify admin: {e}", flush=True)

    return {
        "ok": True,
        "message": "הבקשה התקבלה. ניצור איתך קשר עם קוד אימות בהקדם.",
    }


def _require_debug_token(token: str | None) -> None:
    """Gate debug endpoints behind DEBUG_TOKEN env var.

    Set DEBUG_TOKEN in Railway → Variables, then call:
      /api/v1/auth/debug-admin-whatsapp?debug_token=<value>&phone=...
    """
    import os, hmac
    expected = os.getenv("DEBUG_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/debug-admin-whatsapp")
async def debug_admin_whatsapp(
    debug_token: str | None = None,
    phone: str | None = None,
    recheck: str | None = None,
):
    """Debug endpoint — sends a test WhatsApp and returns full Twilio response.

    Requires DEBUG_TOKEN env var set; pass as ?debug_token=<value>.

    Query params:
      phone:   override target phone (default: ADMIN_PHONE env var)
      recheck: a Twilio message SID — skip sending, just fetch its current status
    """
    _require_debug_token(debug_token)
    import os, httpx

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

    result = {
        "ADMIN_PHONE_set": bool(os.getenv("ADMIN_PHONE")),
        "ADMIN_PHONE_value": os.getenv("ADMIN_PHONE", "(not set)"),
        "TWILIO_ACCOUNT_SID_set": bool(account_sid),
        "TWILIO_AUTH_TOKEN_set": bool(auth_token),
        "TWILIO_WHATSAPP_NUMBER": whatsapp_number,
    }

    if not account_sid or not auth_token:
        result["error"] = "TWILIO_ACCOUNT_SID או TWILIO_AUTH_TOKEN חסר ב-Railway Variables"
        return result

    # Re-check an existing message's status
    if recheck:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{recheck}.json",
                    auth=(account_sid, auth_token),
                    timeout=10.0,
                )
                result["recheck_http_status"] = resp.status_code
                result["recheck_body"] = resp.json() if resp.status_code == 200 else resp.text
        except Exception as e:
            result["error"] = f"Recheck exception: {e}"
        return result

    target = phone or os.getenv("ADMIN_PHONE", "")
    if not target:
        result["error"] = "ADMIN_PHONE לא מוגדר וגם לא הועבר ?phone=..."
        return result

    clean = target.replace("-", "").replace(" ", "")
    if not clean.startswith("+"):
        clean = "+972" + clean.lstrip("0")
    result["target_phone"] = clean

    try:
        payload = {
            "From": f"whatsapp:{whatsapp_number}",
            "To": f"whatsapp:{clean}",
            "Body": "🔔 *בדיקה מ-ShiftWise*\n\nאם קיבלת את ההודעה הזו — ה-WhatsApp עובד מצוין! 🎉",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data=payload,
                timeout=15.0,
            )
            result["twilio_http_status"] = resp.status_code
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}

            # Surface the key diagnostic fields directly
            result["twilio_sid"] = body.get("sid")
            result["twilio_status"] = body.get("status")
            result["twilio_error_code"] = body.get("error_code") or body.get("code")
            result["twilio_error_message"] = body.get("error_message") or body.get("message")
            result["twilio_more_info"] = body.get("more_info")
            result["twilio_full_response"] = body
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
