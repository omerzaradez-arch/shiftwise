"""
WhatsApp bot webhook via Twilio.

Setup:
1. Create free Twilio account → enable WhatsApp Sandbox
2. In Twilio console → Messaging → WhatsApp Sandbox → Webhook URL:
   https://<backend-railway-url>/api/v1/whatsapp/webhook  (HTTP POST)
3. Each employee sends "join <sandbox-keyword>" to the Twilio sandbox number.
4. Employee phone numbers in the system must match (Israeli format: 05XXXXXXXX).
"""

from fastapi import APIRouter, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from datetime import datetime, timezone, timedelta, date

from app.database import get_db
from app.models import Employee, WhatsAppSession, Organization
from app.models.availability import AvailabilitySubmission, UnavailabilitySlot
from app.models.schedule_week import ScheduleWeek

router = APIRouter()

DAY_NAMES = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]

# Shift type groups for WhatsApp options
MORNING_TYPES = ["morning", "afternoon"]
EVENING_TYPES = ["evening", "night"]

MENU = """👋 שלום! אני *הגשת משמרות* של ShiftWise.

בחר אפשרות:
📅 *משמרת* – המשמרת הבאה שלך
🗓 *סידור* – סידור השבוע
✅ *זמינות* – דווח זמינות לשבוע הבא
❓ *עזרה* – הצג תפריט זה"""


def twiml(message: str) -> Response:
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>'
    return Response(content=xml, media_type="application/xml")


def next_week_sunday() -> date:
    # Israel timezone (UTC+3) for correct "this week" calculation
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    # Python weekday: Mon=0 ... Sun=6
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7  # today is Sunday → go to next Sunday
    return today + timedelta(days=days_until_sunday)


DAY_NAME_TO_IDX = {
    "ראשון": 0, "שני": 1, "שלישי": 2,
    "רביעי": 3, "חמישי": 4, "שישי": 5, "שבת": 6,
}


def week_availability_message(operating_days: list[int], week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    lines = [
        f"📅 *זמינות שבוע {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}*",
        "",
        "בחר לכל יום אחת מהאפשרויות:",
        "1️⃣ בוקר",
        "2️⃣ ערב",
        "3️⃣ כל משמרת",
        "4️⃣ כלום (לא זמין)",
        "",
        "*ימי השבוע:*",
    ]
    for day_idx in operating_days:
        day_date = week_start + timedelta(days=day_idx)
        lines.append(f"• {DAY_NAMES[day_idx]} ({day_date.strftime('%d/%m')})")

    example_lines = [f"{DAY_NAMES[d]}: {i+1}" for i, d in enumerate(operating_days[:4])]
    lines += [
        "",
        "*ענה בפורמט:*",
        *example_lines,
        "...",
        "",
        "_ימים שלא ציינת יחשבו כ\"כל משמרת\"_",
        "_לביטול שלח: לא_",
    ]
    return "\n".join(lines)


def parse_day_response(body: str, operating_days: list[int]) -> dict | None:
    """
    Parses responses like:
      ראשון: 1 שני: 4 שלישי: 2 ...
    Returns {str(day_idx): option} or None if parsing fails.
    """
    import re
    responses: dict = {}
    # Match "day_name: number" with flexible spacing/punctuation
    pattern = re.compile(
        r'(ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)\s*[:\-]\s*([1-4])',
        re.UNICODE
    )
    for match in pattern.finditer(body):
        day_name, num = match.group(1), match.group(2)
        day_idx = DAY_NAME_TO_IDX.get(day_name)
        if day_idx is not None and day_idx in operating_days:
            option = OPTION_MAP.get(num)
            if option:
                responses[str(day_idx)] = option
    return responses if responses else None


OPTION_MAP = {
    "1": {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "2": {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "3": {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "4": {"available": False, "preferred_types": [],            "is_hard": True,  "label": "כלום"},
    # text aliases
    "בוקר":       {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "ב":          {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "ערב":        {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "ע":          {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "כל":         {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "כל משמרת":  {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "הכל":        {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "כלום":       {"available": False, "preferred_types": [],            "is_hard": True,  "label": "כלום"},
    "כ":          {"available": False, "preferred_types": [],            "is_hard": True,  "label": "כלום"},
    "לא":         {"available": False, "preferred_types": [],            "is_hard": True,  "label": "כלום"},
}


async def get_session(phone: str, db: AsyncSession) -> WhatsAppSession:
    session = await db.get(WhatsAppSession, phone)
    if not session:
        session = WhatsAppSession(phone=phone, state="idle", context={})
        db.add(session)
        await db.flush()
    return session


async def find_employee(phone: str, db: AsyncSession) -> Employee | None:
    clean = phone.replace("+972", "0").replace("+", "").replace("-", "").strip()
    last9 = clean[-9:] if len(clean) >= 9 else clean
    result = await db.execute(
        select(Employee).where(Employee.is_active == True)
    )
    for emp in result.scalars().all():
        emp_clean = (emp.phone or "").replace("-", "").replace(" ", "")
        if emp_clean == clean or emp_clean.endswith(last9):
            return emp
    return None


async def get_org_operating_days(org_id: str, db: AsyncSession) -> list[int]:
    org = await db.get(Organization, org_id)
    if org and org.settings:
        days = org.settings.get("operating_days")
        if days is not None:
            return days
    return [0, 1, 2, 3, 4, 5]


# ── Commands ───────────────────────────────────────────────────────────────────

async def cmd_next_shift(employee: Employee, db: AsyncSession) -> str:
    from app.models.scheduled_shift import ScheduledShift
    from app.models.shift_template import ShiftTemplate
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= today,
            ScheduledShift.status != "cancelled",
        ).order_by(ScheduledShift.date, ScheduledShift.start_time).limit(1)
    )
    shift = result.scalar_one_or_none()
    if not shift:
        return "😊 אין לך משמרות מתוכננות בקרוב."
    our_dow = (shift.date.weekday() + 1) % 7
    tmpl = await db.get(ShiftTemplate, shift.template_id) if shift.template_id else None
    name = tmpl.name if tmpl else "משמרת"
    return (
        f"📅 *המשמרת הבאה שלך:*\n"
        f"{name} – יום {DAY_NAMES[our_dow]} {shift.date.strftime('%d/%m')}\n"
        f"🕐 {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"
    )


async def cmd_week_schedule(employee: Employee, db: AsyncSession) -> str:
    from app.models.scheduled_shift import ScheduledShift
    from app.models.shift_template import ShiftTemplate
    today = datetime.now(timezone.utc).date()
    our_dow_today = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=our_dow_today)
    week_end = week_start + timedelta(days=6)
    result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= week_start,
            ScheduledShift.date <= week_end,
            ScheduledShift.status != "cancelled",
        ).order_by(ScheduledShift.date, ScheduledShift.start_time)
    )
    shifts = result.scalars().all()
    if not shifts:
        return "😊 אין לך משמרות השבוע."
    lines = [f"🗓 *הסידור שלך השבוע ({week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}):*"]
    for s in shifts:
        dow = (s.date.weekday() + 1) % 7
        lines.append(f"• יום {DAY_NAMES[dow]} {s.date.strftime('%d/%m')}: {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}")
    return "\n".join(lines)


# ── Availability flow ──────────────────────────────────────────────────────────

def build_summary(responses: dict, operating_days: list[int], week_start: date) -> str:
    lines = [f"📋 *סיכום זמינות שבוע {week_start.strftime('%d/%m')}:*"]
    for day_idx in operating_days:
        resp = responses.get(str(day_idx))
        if resp:
            label = resp.get("label", "?")
        else:
            label = "זמין לכל"
        lines.append(f"• {DAY_NAMES[day_idx]}: {label}")
    lines.append("\nלאשר שלח *כן*, לביטול שלח *לא*")
    return "\n".join(lines)


async def save_availability(
    employee: Employee,
    week_start: date,
    operating_days: list[int],
    responses: dict,
    db: AsyncSession,
) -> str:
    week_end = week_start + timedelta(days=6)

    # Upsert ScheduleWeek
    week_result = await db.execute(
        select(ScheduleWeek).where(
            ScheduleWeek.org_id == employee.org_id,
            ScheduleWeek.week_start == week_start,
        )
    )
    week = week_result.scalar_one_or_none()
    if not week:
        import uuid
        week = ScheduleWeek(
            id=str(uuid.uuid4()),
            org_id=employee.org_id,
            week_start=week_start,
            week_end=week_end,
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

    # Build day_preferences dict
    day_prefs: dict = {}
    for day_idx in operating_days:
        resp = responses.get(str(day_idx))
        if resp:
            day_prefs[str(day_idx)] = {
                "available": resp["available"],
                "preferred_types": resp.get("preferred_types", []),
                "is_hard": resp.get("is_hard", False),
            }

    if sub:
        # Clear old unavailability slots
        from sqlalchemy import delete
        await db.execute(
            delete(UnavailabilitySlot).where(UnavailabilitySlot.submission_id == sub.id)
        )
        sub.day_preferences = day_prefs
    else:
        import uuid
        sub = AvailabilitySubmission(
            id=str(uuid.uuid4()),
            employee_id=employee.id,
            week_id=week.id,
            day_preferences=day_prefs,
        )
        db.add(sub)
        await db.flush()

    # Add UnavailabilitySlots for unavailable days
    for day_idx in operating_days:
        resp = responses.get(str(day_idx))
        if not resp or resp["available"]:
            continue
        import uuid
        slot_date = week_start + timedelta(days=day_idx)
        db.add(UnavailabilitySlot(
            id=str(uuid.uuid4()),
            submission_id=sub.id,
            date=slot_date,
            is_hard_constraint=resp.get("is_hard", False),
        ))

    await db.commit()
    return f"✅ *הזמינות נשמרה לשבוע {week_start.strftime('%d/%m')}!*\nתודה {employee.name} 🙏"


# ── Main webhook ───────────────────────────────────────────────────────────────

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    raw_from = str(form.get("From", ""))
    body = str(form.get("Body", "")).strip()
    phone = raw_from.replace("whatsapp:", "")

    employee = await find_employee(phone, db)
    if not employee:
        return twiml("❌ מספר הטלפון שלך לא מזוהה במערכת.\nפנה למנהל שלך לחיבור הטלפון לחשבון.")

    session = await get_session(phone, db)

    # Auto-expire sessions older than 15 min
    if session.updated_at:
        age = (datetime.now(timezone.utc) - session.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
        if age > 900 and session.state != "idle":
            session.state = "idle"
            session.context = {}
            await db.commit()

    normalized = body.lower().strip()

    # ── Global cancel ──
    if normalized in ("לא", "ביטול", "cancel", "בטל"):
        session.state = "idle"
        session.context = {}
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return twiml("❌ הפעולה בוטלה.\n\n" + MENU)

    # ── State: waiting for day-by-day response ──
    if session.state == "availability_waiting_response":
        ctx = dict(session.context or {})
        operating_days: list[int] = ctx.get("operating_days", [0, 1, 2, 3, 4, 5])
        week_start_str: str = ctx.get("week_start", "")
        week_start = date.fromisoformat(week_start_str)

        responses = parse_day_response(body, operating_days)

        if not responses:
            return twiml(
                "⚠️ לא הצלחתי לקרוא את התשובה.\n"
                "שלח בפורמט:\nראשון: 1\nשני: 3\nשלישי: 2 ...\n\n"
                + week_availability_message(operating_days, week_start)
            )

        # Fill missing days with "כל משמרת" (option 3)
        for day_idx in operating_days:
            if str(day_idx) not in responses:
                responses[str(day_idx)] = OPTION_MAP["3"]

        ctx["responses"] = responses
        session.state = "availability_confirm"
        session.context = ctx
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return twiml(build_summary(responses, operating_days, week_start))

    # ── State: confirmation ──
    if session.state == "availability_confirm":
        ctx = dict(session.context or {})
        if normalized in ("כן", "yes", "אישור", "אשר", "ok", "✅"):
            week_start = date.fromisoformat(ctx["week_start"])
            operating_days = ctx.get("operating_days", [0, 1, 2, 3, 4, 5])
            responses = ctx.get("responses", {})
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            msg = await save_availability(employee, week_start, operating_days, responses, db)
            return twiml(msg)
        else:
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return twiml("❌ הזמינות לא נשמרה.\n\n" + MENU)

    # ── Stateless commands ──
    if any(kw in normalized for kw in ["שלום", "היי", "תפריט", "עזרה", "עזור", "menu", "help", "hello", "hi"]):
        return twiml(MENU)

    if "זמינות" in normalized:
        week_start = next_week_sunday()
        operating_days = await get_org_operating_days(employee.org_id, db)
        if not operating_days:
            return twiml("⚠️ לא הוגדרו ימי פעילות לעסק. פנה למנהל.")
        session.state = "availability_waiting_response"
        session.context = {
            "week_start": week_start.isoformat(),
            "operating_days": operating_days,
        }
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return twiml(week_availability_message(operating_days, week_start))

    if "משמרת" in normalized or "הבא" in normalized:
        return twiml(await cmd_next_shift(employee, db))

    if "סידור" in normalized or "שבוע" in normalized:
        return twiml(await cmd_week_schedule(employee, db))

    return twiml(MENU)
