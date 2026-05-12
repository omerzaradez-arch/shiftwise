"""
WhatsApp bot webhook via Twilio.

Setup:
1. Add TWILIO_AUTH_TOKEN to Railway env vars (for request validation)
2. In Twilio console → Messaging → WhatsApp Sandbox → set webhook to:
   https://<your-backend-domain>/api/v1/whatsapp/webhook
3. Employees must send "join <sandbox-keyword>" to the Twilio sandbox number first.
"""

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models import Employee, WhatsAppSession, ScheduledShift, ShiftTemplate
from app.models.schedule_week import ScheduleWeek

router = APIRouter()

# ── TwiML helpers ──────────────────────────────────────────────────────────────

def twiml(message: str) -> Response:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Message>{message}</Message></Response>"""
    return Response(content=xml, media_type="application/xml")


# ── Text constants ──────────────────────────────────────────────────────────────

MENU = """👋 שלום! אני ShiftWise Bot.

בחר אפשרות:
📅 *משמרת* – המשמרת הבאה שלך
🗓 *סידור* – סידור השבוע הנוכחי
✅ *זמינות* – דווח זמינות לשבוע הבא
❓ *עזרה* – הצג תפריט זה"""

AVAILABILITY_PROMPT = """📅 *דיווח זמינות לשבוע הבא*

שלח את המספרים של הימים שאינך זמין לעבוד:
1 = ראשון
2 = שני
3 = שלישי
4 = רביעי
5 = חמישי
6 = שישי
7 = שבת

לדוגמה: 3,5 (לא זמין ברביעי ושישי)
אם אתה זמין כל השבוע שלח: _אין_"""

DAY_NAMES = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]

# ── Session helpers ─────────────────────────────────────────────────────────────

async def get_session(phone: str, db: AsyncSession) -> WhatsAppSession:
    session = await db.get(WhatsAppSession, phone)
    if not session:
        session = WhatsAppSession(phone=phone)
        db.add(session)
        await db.flush()
    return session


async def reset_session(session: WhatsAppSession, db: AsyncSession):
    session.state = "idle"
    session.context = {}
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ── Business logic handlers ─────────────────────────────────────────────────────

async def cmd_next_shift(employee: Employee, db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(ScheduledShift)
        .where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= today,
            ScheduledShift.status != "cancelled",
        )
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
        .limit(1)
    )
    shift = result.scalar_one_or_none()
    if not shift:
        return "😊 אין לך משמרות מתוכננות בקרוב."

    day_name = DAY_NAMES[shift.date.weekday() % 7] if shift.date.weekday() < 7 else ""
    template = await db.get(ShiftTemplate, shift.template_id) if shift.template_id else None
    name = template.name if template else "משמרת"
    return (
        f"📅 *המשמרת הבאה שלך:*\n"
        f"{name} – יום {day_name} {shift.date.strftime('%d/%m')}\n"
        f"🕐 {shift.start_time.strftime('%H:%M')} – {shift.end_time.strftime('%H:%M')}"
    )


async def cmd_week_schedule(employee: Employee, db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
    week_end = week_start + timedelta(days=6)

    result = await db.execute(
        select(ScheduledShift)
        .where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= week_start,
            ScheduledShift.date <= week_end,
            ScheduledShift.status != "cancelled",
        )
        .order_by(ScheduledShift.date, ScheduledShift.start_time)
    )
    shifts = result.scalars().all()
    if not shifts:
        return "😊 אין לך משמרות השבוע."

    lines = ["🗓 *הסידור שלך השבוע:*"]
    for s in shifts:
        day_idx = (s.date.weekday() + 1) % 7
        lines.append(f"• יום {DAY_NAMES[day_idx]} {s.date.strftime('%d/%m')}: {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}")
    return "\n".join(lines)


async def cmd_start_availability(session: WhatsAppSession, db: AsyncSession) -> str:
    session.state = "availability_select_days"
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return AVAILABILITY_PROMPT


async def cmd_submit_availability(
    employee: Employee, body: str, session: WhatsAppSession, db: AsyncSession
) -> str:
    from app.models.availability import AvailabilitySubmission, UnavailabilitySlot
    from app.models.schedule_week import ScheduleWeek

    today = datetime.now(timezone.utc).date()
    days_until_sunday = (6 - today.weekday()) % 7 + 1 if today.weekday() != 6 else 7
    next_sunday = today + timedelta(days=days_until_sunday if today.weekday() != 6 else 0)
    if today.weekday() == 6:
        next_sunday = today + timedelta(days=7)

    blocked: list[int] = []
    normalized = body.strip().lower()
    if normalized not in ("אין", "ain", "0", "none"):
        for part in normalized.replace(" ", "").split(","):
            try:
                n = int(part)
                if 1 <= n <= 7:
                    blocked.append(n - 1)
            except ValueError:
                pass

    # Upsert ScheduleWeek
    week_result = await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == employee.org_id,
            ScheduleWeek.week_start == next_sunday,
        )
    )
    week = week_result.scalar_one_or_none()
    if not week:
        week = ScheduleWeek(
            org_id=employee.org_id,
            week_start=next_sunday,
            week_end=next_sunday + timedelta(days=6),
            status="collecting",
        )
        db.add(week)
        await db.flush()

    # Upsert AvailabilitySubmission
    sub_result = await db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.employee_id == employee.id,
            AvailabilitySubmission.week_id == week.id,
        )
    )
    sub = sub_result.scalar_one_or_none()
    if sub:
        await db.execute(
            __import__("sqlalchemy", fromlist=["delete"]).delete(UnavailabilitySlot).where(
                UnavailabilitySlot.submission_id == sub.id
            )
        )
    else:
        sub = AvailabilitySubmission(employee_id=employee.id, week_id=week.id)
        db.add(sub)
        await db.flush()

    for day_idx in blocked:
        date = next_sunday + timedelta(days=day_idx)
        slot = UnavailabilitySlot(submission_id=sub.id, date=date, is_hard_constraint=True)
        db.add(slot)

    await db.commit()
    await reset_session(session, db)

    if not blocked:
        return f"✅ נרשמת כזמין כל ימי שבוע {next_sunday.strftime('%d/%m')}!"
    day_labels = [DAY_NAMES[d] for d in blocked]
    return f"✅ הזמינות נשמרה לשבוע {next_sunday.strftime('%d/%m')}!\nימים חסומים: {', '.join(day_labels)}"


# ── Main webhook ────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    raw_from = form.get("From", "")
    body = str(form.get("Body", "")).strip()
    phone = raw_from.replace("whatsapp:", "").replace("+972", "0").replace("+", "")

    # Find employee by phone
    result = await db.execute(
        select(Employee).where(Employee.phone == phone, Employee.is_active == True)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        # Try with country code
        result2 = await db.execute(
            select(Employee).where(Employee.phone.contains(phone[-9:]), Employee.is_active == True)
        )
        employee = result2.scalar_one_or_none()

    if not employee:
        return twiml("❌ מספר הטלפון שלך לא מזוהה במערכת.\nפנה למנהל שלך לחיבור הטלפון לחשבון.")

    session = await get_session(phone, db)

    # Expire sessions older than 10 minutes
    if session.updated_at:
        age = datetime.now(timezone.utc) - session.updated_at.replace(tzinfo=timezone.utc)
        if age.total_seconds() > 600 and session.state != "idle":
            await reset_session(session, db)

    normalized = body.lower()

    # ── State: waiting for availability days ──
    if session.state == "availability_select_days":
        msg = await cmd_submit_availability(employee, body, session, db)
        return twiml(msg)

    # ── Stateless commands ──
    if any(kw in normalized for kw in ["שלום", "היי", "תפריט", "menu", "עזרה", "עזור", "help", "hello", "hi"]):
        return twiml(MENU)
    if "זמינות" in normalized:
        msg = await cmd_start_availability(session, db)
        return twiml(msg)
    if "משמרת" in normalized or "הבא" in normalized:
        msg = await cmd_next_shift(employee, db)
        return twiml(msg)
    if "סידור" in normalized or "שבוע" in normalized:
        msg = await cmd_week_schedule(employee, db)
        return twiml(msg)

    # Default: show menu
    return twiml(MENU)
