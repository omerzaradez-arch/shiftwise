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

MENU = """👋 שלום! אני *ShiftWise* – ניהול משמרות חכם.

🟢 *כניסה* – כניסה לעבודה
🔴 *יציאה* – יציאה מהעבודה
📊 *שעות* – שעות ושכר החודש
─────────────────
📅 *משמרת* – המשמרת הבאה שלך
🗓 *סידור* – סידור השבוע
✅ *זמינות* – דווח זמינות לשבוע הבא
🔄 *לא יכול* – בקש החלפת משמרת
❓ *עזרה* – הצג תפריט זה"""


def twiml(message: str) -> Response:
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>'
    return Response(content=xml, media_type="application/xml")


def empty_twiml() -> Response:
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


def _normalize_phone(phone: str) -> str:
    clean = phone.replace("-", "").replace(" ", "")
    if not clean.startswith("+"):
        clean = "+972" + clean.lstrip("0")
    return clean


async def _twilio_send_interactive(phone: str, content_payload: dict) -> bool:
    """Create a Twilio Content template and send it as an interactive message."""
    import os, httpx
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    if not account_sid or not auth_token:
        return False
    clean = _normalize_phone(phone)
    try:
        async with httpx.AsyncClient() as client:
            create = await client.post(
                "https://content.twilio.com/v1/Content",
                auth=(account_sid, auth_token),
                json=content_payload,
                timeout=10.0,
            )
            if create.status_code not in (200, 201):
                print(f"[twilio-interactive] CREATE failed {create.status_code}: {create.text[:200]}", flush=True)
                return False
            sid = create.json()["sid"]
            send = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={"From": f"whatsapp:{from_number}", "To": f"whatsapp:{clean}", "ContentSid": sid},
                timeout=10.0,
            )
            ok = send.status_code == 201
            if not ok:
                print(f"[twilio-interactive] SEND failed {send.status_code}: {send.text[:200]}", flush=True)
            return ok
    except Exception as e:
        print(f"[twilio-interactive] exception: {e}", flush=True)
        return False


async def send_interactive_day_question(
    phone: str, day_idx: int, day_date: date,
    week_start: date, week_end: date, current: int, total: int,
) -> bool:
    """Send availability day question as a WhatsApp list picker."""
    import uuid
    body = (
        f"📅 זמינות שבוע {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')} "
        f"({current}/{total})\n\n"
        f"*{DAY_NAMES[day_idx]} {day_date.strftime('%d/%m')}* — מה הזמינות שלך?"
    )
    payload = {
        "friendly_name": f"sw_avail_{uuid.uuid4().hex[:8]}",
        "language": "he",
        "types": {
            "twilio/list-picker": {
                "body": body,
                "button": "בחר זמינות",
                "items": [
                    {"id": "1", "item": "בוקר"},
                    {"id": "2", "item": "ערב"},
                    {"id": "3", "item": "כל משמרת"},
                    {"id": "4", "item": "לא זמין"},
                ],
            }
        },
    }
    return await _twilio_send_interactive(phone, payload)


async def send_interactive_shift_list(phone: str, shifts_data: list[dict]) -> bool:
    """Send shift selection as a WhatsApp list picker. shifts_data: [{"display": str}, ...]"""
    import uuid
    payload = {
        "friendly_name": f"sw_shifts_{uuid.uuid4().hex[:8]}",
        "language": "he",
        "types": {
            "twilio/list-picker": {
                "body": "🔄 *בקשת החלפת משמרת*\n\nלאיזו משמרת אינך יכול/ה להגיע?",
                "button": "בחר משמרת",
                "items": [
                    {"id": str(i + 1), "item": d["display"]}
                    for i, d in enumerate(shifts_data)
                ],
            }
        },
    }
    return await _twilio_send_interactive(phone, payload)


async def send_interactive_confirm(phone: str, body: str) -> bool:
    """Send yes/no quick-reply buttons."""
    import uuid
    payload = {
        "friendly_name": f"sw_confirm_{uuid.uuid4().hex[:8]}",
        "language": "he",
        "types": {
            "twilio/quick-reply": {
                "body": body,
                "actions": [
                    {"title": "כן", "id": "כן"},
                    {"title": "לא", "id": "לא"},
                ],
            }
        },
    }
    return await _twilio_send_interactive(phone, payload)


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


def day_question_message(day_idx: int, day_date: date, week_start: date, week_end: date, current: int, total: int) -> str:
    return (
        f"📅 *זמינות שבוע {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}* ({current}/{total})\n\n"
        f"*{DAY_NAMES[day_idx]} {day_date.strftime('%d/%m')}* — מה הזמינות שלך?\n\n"
        f"1️⃣ בוקר\n"
        f"2️⃣ ערב\n"
        f"3️⃣ כל משמרת\n"
        f"4️⃣ לא זמין\n\n"
        f"_שלח 1 / 2 / 3 / 4_\n_לביטול שלח: ביטול_"
    )


def parse_day_response(body: str, operating_days: list[int]) -> dict | None:
    """
    Parses responses like:
      ראשון: בוקר שני: לא שלישי: ערב ...
      ראשון: 1 שני: 4 שלישי: 2 ...  (numbers still supported)
    Returns {str(day_idx): option} or None if parsing fails.
    """
    import re
    responses: dict = {}
    # (?:^|[\s,\n\r]) — day name must start at line beginning or after whitespace/comma
    # (?![\u05d0-\u05ea]) — option must NOT be followed by another Hebrew letter (word boundary)
    pattern = re.compile(
        r'(?:(?:^|[\s,\n\r]))(ראשון|שני|שלישי|רביעי|חמישי|שישי|שבת)\s*[:\-]\s*'
        r'(כל משמרת|כל|הכל|בוקר|ערב|כלום|לא|[1-4])(?![\u05d0-\u05ea])',
        re.UNICODE | re.MULTILINE
    )
    for match in pattern.finditer(body):
        day_name, value = match.group(1), match.group(2).strip()
        day_idx = DAY_NAME_TO_IDX.get(day_name)
        if day_idx is not None and day_idx in operating_days:
            option = OPTION_MAP.get(value)
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
    "לא זמין":    {"available": False, "preferred_types": [],            "is_hard": True,  "label": "כלום"},
}


async def send_whatsapp_to(phone: str, body: str, media_url: str | None = None) -> bool:
    import os, httpx
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    if not account_sid or not auth_token:
        return False
    clean = phone.replace("-", "").replace(" ", "")
    if not clean.startswith("+"):
        clean = "+972" + clean.lstrip("0")
    try:
        payload = {
            "From": f"whatsapp:{whatsapp_number}",
            "To": f"whatsapp:{clean}",
            "Body": body,
        }
        if media_url:
            payload["MediaUrl"] = media_url
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data=payload,
                timeout=10.0,
            )
            if resp.status_code != 201:
                print(f"[twilio] ERROR {resp.status_code}: {resp.text}", flush=True)
            else:
                body = resp.json()
                print(f"[twilio] OK to={clean} sid={body.get('sid')} status={body.get('status')} error={body.get('error_code')}", flush=True)
            return resp.status_code == 201
    except Exception as e:
        print(f"[twilio] exception: {e}", flush=True)
        return False


async def cmd_cant_come(employee: Employee, db: AsyncSession) -> tuple[str, list[str]]:
    from app.models.scheduled_shift import ScheduledShift
    from datetime import time as dt_time
    now_il = datetime.now(timezone.utc) + timedelta(hours=3)
    today = now_il.date()
    now_time = now_il.time()
    week_end = today + timedelta(days=7)

    result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= today,
            ScheduledShift.date <= week_end,
            ScheduledShift.status.in_(["assigned", "swap_requested"]),
        ).order_by(ScheduledShift.date, ScheduledShift.start_time)
    )
    all_shifts = result.scalars().all()

    # Filter out shifts that have already started or ended today
    shifts = []
    for s in all_shifts:
        if s.date == today:
            shift_start = s.start_time if isinstance(s.start_time, dt_time) else s.start_time
            if shift_start <= now_time:
                continue  # already started — skip
        shifts.append(s)

    if not shifts:
        return "😊 אין לך משמרות עתידיות שניתן להחליף.\n_(ניתן לבקש החלפה רק למשמרות שטרם התחילו)_", []

    lines = ["🔄 *בקשת החלפת משמרת*\n", "לאיזו משמרת אינך יכול/ה להגיע?"]
    shift_ids = []
    for i, s in enumerate(shifts, 1):
        dow = (s.date.weekday() + 1) % 7
        lines.append(f"{i}. יום {DAY_NAMES[dow]} {s.date.strftime('%d/%m')} {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}")
        shift_ids.append(s.id)
    lines.append("\n_שלח את מספר המשמרת_\n_לביטול שלח: לא_")
    return "\n".join(lines), shift_ids


async def find_and_notify_replacements(
    shift_id: str, requester_name: str, org_id: str, db: AsyncSession
) -> int:
    from app.models.scheduled_shift import ScheduledShift
    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        return 0
    dow = (shift.date.weekday() + 1) % 7
    shift_display = f"יום {DAY_NAMES[dow]} {shift.date.strftime('%d/%m')} {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"

    result = await db.execute(
        select(Employee).where(
            Employee.org_id == org_id,
            Employee.is_active == True,
            Employee.id != shift.employee_id,
            Employee.phone != None,
        )
    )
    all_employees = result.scalars().all()

    # Exclude employees already in the same shift (same date + same start time)
    same_shift_result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.date == shift.date,
            ScheduledShift.start_time == shift.start_time,
            ScheduledShift.status.notin_(["cancelled"]),
        )
    )
    same_shift_ids = {s.employee_id for s in same_shift_result.scalars().all()}
    candidates = [e for e in all_employees if e.id not in same_shift_ids]
    sent = 0
    for candidate in candidates:
        msg = (
            f"👋 שלום {candidate.name}!\n"
            f"*{requester_name}* מחפש/ת מחליף/ה למשמרת:\n"
            f"📅 {shift_display}\n\n"
            f"האם תוכל/י להחליף?"
        )
        ok = await send_interactive_confirm(candidate.phone, msg)
        if not ok:
            ok = await send_whatsapp_to(candidate.phone, msg + "\n\nשלח/י *כן* לאישור או *לא* לדחייה")
        if ok:
            sent += 1
            # Normalize phone to match the format used by the webhook (+972XXXXXXXXX)
            norm_phone = candidate.phone.replace("-", "").replace(" ", "")
            if not norm_phone.startswith("+"):
                norm_phone = "+972" + norm_phone.lstrip("0")
            cand_session = await db.get(WhatsAppSession, norm_phone)
            if not cand_session:
                cand_session = WhatsAppSession(phone=norm_phone, state="idle", context={})
                db.add(cand_session)
                await db.flush()
            ctx = dict(cand_session.context or {})
            ctx["pending_swap_shift_id"] = shift_id
            ctx["pending_swap_display"] = shift_display
            ctx["pending_swap_requester"] = requester_name
            cand_session.context = ctx
            cand_session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return sent


async def handle_volunteer_acceptance(employee: Employee, ctx: dict, db: AsyncSession) -> str:
    from app.models.scheduled_shift import ScheduledShift
    shift_id = ctx["pending_swap_shift_id"]
    shift_display = ctx.get("pending_swap_display", "")
    shift = await db.get(ScheduledShift, shift_id)

    if not shift or shift.status not in ("assigned", "swap_requested"):
        return "❌ המשמרת כבר הוחלפה על ידי עובד אחר."

    existing = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date == shift.date,
            ScheduledShift.start_time == shift.start_time,
            ScheduledShift.status != "cancelled",
        )
    )
    if existing.scalar_one_or_none():
        return "❌ כבר יש לך משמרת באותה שעה ביום הזה, לא ניתן לקחת את המשמרת."

    original_emp = await db.get(Employee, shift.employee_id)
    shift.employee_id = employee.id
    shift.status = "assigned"
    await db.commit()

    if original_emp and original_emp.phone:
        await send_whatsapp_to(
            original_emp.phone,
            f"✅ בשורות טובות!\n*{employee.name}* יחליף אותך במשמרת:\n{shift_display}"
        )

    managers = await db.execute(
        select(Employee).where(
            Employee.org_id == employee.org_id,
            Employee.role.in_(["manager", "owner"]),
            Employee.is_active == True,
            Employee.phone != None,
        )
    )
    orig_name = original_emp.name if original_emp else "?"
    for mgr in managers.scalars().all():
        await send_whatsapp_to(
            mgr.phone,
            f"🔄 *עדכון סידור*\n{shift_display}\n{orig_name} ← {employee.name}\n_(החלפה אוטומטית)_"
        )

    return f"✅ *אושר!* קיבלת את המשמרת:\n{shift_display}\n\nהמנהל קיבל עדכון."


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


# ── Attendance commands ────────────────────────────────────────────────────────

from math import radians, sin, cos, sqrt, atan2

def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


async def cmd_checkin(employee: Employee, db: AsyncSession, lat: float | None = None, lng: float | None = None) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()

    existing = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == employee.id,
                Attendance.date == today,
                Attendance.check_out == None,
            )
        )
    )
    if existing.scalar_one_or_none():
        return "⚠️ כבר רשום/ה כניסה היום.\nשלח *יציאה* כשאתה יוצא."

    # Check location
    org = await db.get(Organization, employee.org_id)
    is_valid = True
    location_msg = ""
    if lat is not None and lng is not None and org and org.settings:
        s = org.settings
        biz_lat = s.get("location_lat")
        biz_lng = s.get("location_lng")
        radius = s.get("location_radius", 200)
        if biz_lat and biz_lng:
            dist = _haversine(lat, lng, float(biz_lat), float(biz_lng))
            is_valid = dist <= float(radius)
            if is_valid:
                location_msg = f"\n📍 מיקום אומת ✅ ({int(dist)} מ׳ מהעסק)"
            else:
                location_msg = f"\n⚠️ מיקום לא אומת — נמצאת {int(dist)} מ׳ מהעסק"

    import uuid
    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)
    att = Attendance(
        id=str(uuid.uuid4()),
        employee_id=employee.id,
        org_id=employee.org_id,
        date=today,
        check_in=now_utc,
        check_in_lat=lat,
        check_in_lng=lng,
        is_valid_location=is_valid,
    )
    db.add(att)
    await db.commit()

    return (
        f"🟢 *כניסה נרשמה!*\n"
        f"⏰ {now_il.strftime('%H:%M')}"
        f"{location_msg}\n\n"
        f"שלח *יציאה* כשאתה יוצא מהעבודה."
    )


async def cmd_checkout(employee: Employee, db: AsyncSession) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()

    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == employee.id,
                Attendance.date == today,
                Attendance.check_out == None,
            )
        )
    )
    att = result.scalar_one_or_none()
    if not att:
        return "⚠️ לא נמצאת רשומת כניסה פתוחה להיום.\nשלח *כניסה* כדי להתחיל."

    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)
    total_minutes = int((now_utc - att.check_in.replace(tzinfo=timezone.utc) if att.check_in.tzinfo is None else now_utc - att.check_in).total_seconds() / 60)
    att.check_out = now_utc
    att.total_minutes = total_minutes
    await db.commit()

    hours = total_minutes // 60
    mins = total_minutes % 60
    pay_msg = ""
    if employee.hourly_rate:
        pay = round(employee.hourly_rate * total_minutes / 60, 2)
        pay_msg = f"\n💰 שכר היום: ₪{pay:,.2f}"

    return (
        f"🔴 *יציאה נרשמה!*\n"
        f"⏰ {now_il.strftime('%H:%M')}\n"
        f"⏱ עבדת היום: *{hours}:{mins:02d} שעות*"
        f"{pay_msg}\n\n"
        f"להתראות! 👋"
    )


async def cmd_hours(employee: Employee, db: AsyncSession) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    now_il = datetime.now(timezone.utc) + timedelta(hours=3)
    month = now_il.month
    year = now_il.year
    from_date = date(year, month, 1)
    to_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == employee.id,
                Attendance.date >= from_date,
                Attendance.date < to_date,
                Attendance.check_out != None,
            )
        )
    )
    records = result.scalars().all()
    if not records:
        return "📊 אין נתוני נוכחות לחודש הנוכחי."

    total_minutes = sum(r.total_minutes or 0 for r in records)
    hours = total_minutes // 60
    mins = total_minutes % 60
    days = len(records)

    month_names = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    pay_line = ""
    if employee.hourly_rate:
        pay = round(employee.hourly_rate * total_minutes / 60, 2)
        pay_line = f"\n💰 שכר לתשלום: *₪{pay:,.2f}*\n   (לפי ₪{employee.hourly_rate}/שעה)"

    return (
        f"📊 *נוכחות {month_names[month-1]} {year}*\n\n"
        f"📅 ימים עבדת: *{days}*\n"
        f"⏱ סה״כ שעות: *{hours}:{mins:02d}*"
        f"{pay_line}"
    )


# ── Main webhook ───────────────────────────────────────────────────────────────

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    raw_from = str(form.get("From", ""))
    body = str(form.get("Body", "")).strip()
    phone = raw_from.replace("whatsapp:", "")

    # Handle location messages from WhatsApp
    lat_str = form.get("Latitude")
    lng_str = form.get("Longitude")
    incoming_lat = float(lat_str) if lat_str else None
    incoming_lng = float(lng_str) if lng_str else None

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

    # ── State: waiting for location after "כניסה" ──
    if session.state == "checkin_waiting_location":
        if incoming_lat is not None and incoming_lng is not None:
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            msg = await cmd_checkin(employee, db, lat=incoming_lat, lng=incoming_lng)
            return twiml(msg)
        else:
            # No location shared — register anyway without GPS
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            msg = await cmd_checkin(employee, db)
            return twiml(msg)

    # ── If user shared location while idle — treat as check-in ──
    if incoming_lat is not None and incoming_lng is not None and session.state == "idle":
        msg = await cmd_checkin(employee, db, lat=incoming_lat, lng=incoming_lng)
        return twiml(msg)

    # ── Global cancel ──
    if normalized in ("ביטול", "cancel", "בטל"):
        session.state = "idle"
        session.context = {}
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return twiml("❌ הפעולה בוטלה.\n\n" + MENU)

    # ── State: cant_come_selecting ──
    if session.state == "cant_come_selecting":
        ctx = dict(session.context or {})
        shift_ids: list[str] = ctx.get("shift_ids", [])
        shift_displays: list[str] = ctx.get("shift_displays", [])

        # Reset and re-handle if user sends a top-level command
        RESET_KEYWORDS = ["שלום", "היי", "עזרה", "תפריט", "זמינות", "משמרת", "סידור",
                          "שעות", "שכר", "כניסה", "יציאה", "לא יכול", "לא יכולה",
                          "החלפה", "בקשת החלפה", "לא", "no"]
        if any(kw in normalized for kw in RESET_KEYWORDS):
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            # fall through to stateless command handlers below

        else:
            # Support both numeric input and button-click (display text)
            idx = -1
            try:
                idx = int(body.strip()) - 1
                if idx < 0 or idx >= len(shift_ids):
                    idx = -1
            except (ValueError, TypeError):
                pass
            if idx == -1 and body.strip() in shift_displays:
                idx = shift_displays.index(body.strip())
            if idx < 0 or idx >= len(shift_ids):
                return twiml(f"⚠️ שלח מספר בין 1 ל-{len(shift_ids)}.\n_לביטול שלח: לא_")

            from app.models.scheduled_shift import ScheduledShift
            shift = await db.get(ScheduledShift, shift_ids[idx])
            if not shift:
                session.state = "idle"
                session.context = {}
                await db.commit()
                return twiml("❌ המשמרת לא נמצאה.\n\n" + MENU)
            dow = (shift.date.weekday() + 1) % 7
            shift_display = f"יום {DAY_NAMES[dow]} {shift.date.strftime('%d/%m')} {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"
            ctx["selected_shift_id"] = shift.id
            ctx["selected_shift_display"] = shift_display
            session.state = "cant_come_confirm"
            session.context = ctx
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            confirm_body = f"🔄 *אישור בקשת החלפה*\n\n📅 {shift_display}\n\nלאשר את הבקשה?"
            sent = await send_interactive_confirm(phone, confirm_body)
            if sent:
                return empty_twiml()
            return twiml(f"🔄 *אישור בקשת החלפה*\n\n📅 {shift_display}\n\nלאשר שלח *כן*, לביטול שלח *לא*")

    # ── State: cant_come_confirm ──
    if session.state == "cant_come_confirm":
        ctx = dict(session.context or {})
        if normalized in ("כן", "yes", "אישור", "אשר", "ok", "✅"):
            shift_id = ctx.get("selected_shift_id")
            shift_display = ctx.get("selected_shift_display", "")
            from app.models.scheduled_shift import ScheduledShift
            shift = await db.get(ScheduledShift, shift_id)
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            if shift:
                shift.status = "swap_requested"
            await db.commit()
            sent = await find_and_notify_replacements(shift_id, employee.name, employee.org_id, db)
            if sent > 0:
                return twiml(
                    f"✅ הבקשה נשלחה!\n"
                    f"📅 {shift_display}\n\n"
                    f"נשלחה הודעה ל-{sent} עובדים. תקבל/י עדכון כשמישהו יאשר."
                )
            else:
                return twiml(
                    f"⚠️ לא נמצאו עובדים זמינים להחלפה.\n"
                    f"פנה/י ישירות למנהל."
                )
        else:
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return twiml("❌ הבקשה בוטלה.\n\n" + MENU)

    # ── State: day-by-day availability ──
    if session.state == "availability_day_by_day":
        ctx = dict(session.context or {})
        operating_days: list[int] = ctx.get("operating_days", [0, 1, 2, 3, 4, 5])
        week_start_str: str = ctx.get("week_start", "")
        week_start = date.fromisoformat(week_start_str)
        week_end = week_start + timedelta(days=6)
        responses: dict = ctx.get("responses", {})
        step: int = ctx.get("step", 0)

        option = OPTION_MAP.get(normalized) or OPTION_MAP.get(body.strip())
        if not option:
            current_day_idx = operating_days[step]
            current_date = week_start + timedelta(days=current_day_idx)
            return twiml(
                "⚠️ לא הבנתי, שלח 1 / 2 / 3 / 4\n\n"
                + day_question_message(current_day_idx, current_date, week_start, week_end, step + 1, len(operating_days))
            )

        current_day_idx = operating_days[step]
        responses[str(current_day_idx)] = option
        step += 1

        if step < len(operating_days):
            next_day_idx = operating_days[step]
            next_date = week_start + timedelta(days=next_day_idx)
            ctx["responses"] = responses
            ctx["step"] = step
            session.context = ctx
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            sent = await send_interactive_day_question(phone, next_day_idx, next_date, week_start, week_end, step + 1, len(operating_days))
            if sent:
                return empty_twiml()
            return twiml(day_question_message(next_day_idx, next_date, week_start, week_end, step + 1, len(operating_days)))

        # All days answered → show summary with yes/no buttons
        ctx["responses"] = responses
        session.state = "availability_confirm"
        session.context = ctx
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        summary = build_summary(responses, operating_days, week_start)
        sent = await send_interactive_confirm(phone, summary)
        if sent:
            return empty_twiml()
        return twiml(summary)

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
        week_end = week_start + timedelta(days=6)
        first_day_idx = operating_days[0]
        first_date = week_start + timedelta(days=first_day_idx)
        session.state = "availability_day_by_day"
        session.context = {
            "week_start": week_start.isoformat(),
            "operating_days": operating_days,
            "responses": {},
            "step": 0,
        }
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        sent = await send_interactive_day_question(phone, first_day_idx, first_date, week_start, week_end, 1, len(operating_days))
        if sent:
            return empty_twiml()
        return twiml(day_question_message(first_day_idx, first_date, week_start, week_end, 1, len(operating_days)))

    if "משמרת" in normalized or "הבא" in normalized:
        return twiml(await cmd_next_shift(employee, db))

    if "סידור" in normalized or "שבוע" in normalized:
        return twiml(await cmd_week_schedule(employee, db))

    if any(kw in normalized for kw in ["לא יכול", "לא יכולה", "החלפה", "מחליף", "להחליף"]):
        msg, shift_ids = await cmd_cant_come(employee, db)
        if shift_ids:
            from app.models.scheduled_shift import ScheduledShift
            shifts_data = []
            for sid in shift_ids:
                s = await db.get(ScheduledShift, sid)
                if s:
                    dow = (s.date.weekday() + 1) % 7
                    shifts_data.append({"display": f"יום {DAY_NAMES[dow]} {s.date.strftime('%d/%m')} {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}"})
            session.state = "cant_come_selecting"
            session.context = {
                "shift_ids": shift_ids,
                "shift_displays": [s["display"] for s in shifts_data],
            }
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            sent = await send_interactive_shift_list(phone, shifts_data)
            if sent:
                return empty_twiml()
        return twiml(msg)

    # ── Check-in ──
    if any(kw in normalized for kw in ["כניסה", "נכנסתי", "התחלתי", "הגעתי"]):
        org = await db.get(Organization, employee.org_id)
        has_location = org and org.settings and org.settings.get("location_lat")
        if has_location:
            session.state = "checkin_waiting_location"
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return twiml(
                "📍 *לאימות כניסה — שתף מיקום*\n\n"
                "לחץ על 📎 ← מיקום ← שלח מיקום נוכחי\n\n"
                "_או שלח כל הודעה אחרת לכניסה ללא אימות מיקום_"
            )
        else:
            msg = await cmd_checkin(employee, db)
            return twiml(msg)

    # ── Check-out ──
    if any(kw in normalized for kw in ["יציאה", "יצאתי", "סיימתי", "עזבתי"]):
        msg = await cmd_checkout(employee, db)
        return twiml(msg)

    # ── Hours/salary ──
    if any(kw in normalized for kw in ["שעות", "שכר", "כמה עבדתי", "נוכחות"]):
        msg = await cmd_hours(employee, db)
        return twiml(msg)

    # Volunteer accepting a replacement offer
    if normalized in ("כן", "yes", "אישור", "אשר", "ok", "✅"):
        ctx = dict(session.context or {})
        if "pending_swap_shift_id" in ctx:
            result_msg = await handle_volunteer_acceptance(employee, ctx, db)
            ctx.pop("pending_swap_shift_id", None)
            ctx.pop("pending_swap_display", None)
            ctx.pop("pending_swap_requester", None)
            session.context = ctx
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return twiml(result_msg)

    return twiml(MENU)
