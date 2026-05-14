"""
WhatsApp bot webhook via Meta Cloud API (interactive buttons & lists).

Setup:
1. developers.facebook.com → Create App → Business
2. Add WhatsApp product → API Setup
3. Webhook URL: https://<backend-url>/api/v1/whatsapp_meta/webhook
4. Verify Token: any string you choose (set as WHATSAPP_META_VERIFY_TOKEN)
5. Subscribe to field: messages
6. Set env vars:
   WHATSAPP_META_TOKEN      = your access token (starts with EAA...)
   WHATSAPP_META_PHONE_ID   = phone number ID (15-digit number)
   WHATSAPP_META_VERIFY_TOKEN = your chosen verify string

Note: Keep existing Twilio webhook for fallback / testing.
"""

import os, httpx
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
MORNING_TYPES = ["morning", "afternoon"]
EVENING_TYPES = ["evening", "night"]

OPTION_MAP = {
    "avail_morning":  {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "avail_evening":  {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "avail_any":      {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "avail_none":     {"available": False, "preferred_types": [],            "is_hard": True,  "label": "לא זמין"},
    # text fallbacks
    "בוקר":      {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "ערב":       {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "כל משמרת": {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "כלום":      {"available": False, "preferred_types": [],            "is_hard": True,  "label": "לא זמין"},
    "לא":        {"available": False, "preferred_types": [],            "is_hard": True,  "label": "לא זמין"},
    "1": {"available": True,  "preferred_types": MORNING_TYPES, "is_hard": False, "label": "בוקר"},
    "2": {"available": True,  "preferred_types": EVENING_TYPES, "is_hard": False, "label": "ערב"},
    "3": {"available": True,  "preferred_types": [],            "is_hard": False, "label": "כל משמרת"},
    "4": {"available": False, "preferred_types": [],            "is_hard": True,  "label": "לא זמין"},
}

DAY_NAME_TO_IDX = {
    "ראשון": 0, "שני": 1, "שלישי": 2,
    "רביעי": 3, "חמישי": 4, "שישי": 5, "שבת": 6,
}

# ── Meta API helpers ────────────────────────────────────────────────────────────

def _meta_headers() -> dict:
    token = os.getenv("WHATSAPP_META_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def _phone_id() -> str:
    return os.getenv("WHATSAPP_META_PHONE_ID", "")

def _normalize_phone(raw: str) -> str:
    """Return phone in E.164 without +, e.g. 972501234567"""
    clean = raw.replace("+", "").replace("-", "").replace(" ", "")
    if clean.startswith("0"):
        clean = "972" + clean[1:]
    return clean


async def send_text(to: str, text: str) -> bool:
    phone = _normalize_phone(to)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    return await _post(payload)


async def send_buttons(to: str, body: str, buttons: list[dict]) -> bool:
    """
    buttons = [{"id": "btn_id", "title": "כותרת"}, ...]  (max 3)
    """
    phone = _normalize_phone(to)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                    for b in buttons[:3]
                ]
            },
        },
    }
    return await _post(payload)


async def send_list(to: str, body: str, sections: list[dict], button_label: str = "בחר") -> bool:
    """
    sections = [{"title": "קטגוריה", "rows": [{"id": "row_id", "title": "כותרת", "description": "תיאור"}, ...]}, ...]
    """
    phone = _normalize_phone(to)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "ShiftWise 📅"},
            "body": {"text": body},
            "action": {
                "button": button_label,
                "sections": sections,
            },
        },
    }
    return await _post(payload)


async def _post(payload: dict) -> bool:
    phone_id = _phone_id()
    if not phone_id or not os.getenv("WHATSAPP_META_TOKEN"):
        print("[meta_wa] ERROR: missing WHATSAPP_META_TOKEN or WHATSAPP_META_PHONE_ID", flush=True)
        return False
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=_meta_headers(), json=payload, timeout=10.0)
            if resp.status_code not in (200, 201):
                print(f"[meta_wa] ERROR {resp.status_code}: {resp.text}", flush=True)
                return False
            print(f"[meta_wa] OK to={payload.get('to')}", flush=True)
            return True
    except Exception as e:
        print(f"[meta_wa] exception: {e}", flush=True)
        return False


# ── Menus ────────────────────────────────────────────────────────────────────────

async def send_main_menu(to: str) -> None:
    await send_list(
        to=to,
        body="👋 שלום! אני *ShiftWise* — ניהול משמרות חכם.\nבחר/י פעולה:",
        sections=[
            {
                "title": "⏱ נוכחות",
                "rows": [
                    {"id": "checkin",   "title": "✅ כניסה לעבודה",   "description": "דווח כניסה עכשיו"},
                    {"id": "checkout",  "title": "🚪 יציאה מהעבודה",  "description": "דווח יציאה עכשיו"},
                    {"id": "hours",     "title": "📊 שעות ושכר",      "description": "סיכום החודש"},
                ],
            },
            {
                "title": "📅 משמרות",
                "rows": [
                    {"id": "next_shift",    "title": "📅 המשמרת הבאה",   "description": "מה המשמרת הבאה שלי?"},
                    {"id": "week_schedule", "title": "🗓 סידור השבוע",    "description": "כל המשמרות השבוע"},
                    {"id": "availability",  "title": "✅ דווח זמינות",    "description": "זמינות לשבוע הבא"},
                    {"id": "cant_come",     "title": "🔄 בקש החלפה",      "description": "לא יכול/ה להגיע"},
                ],
            },
        ],
        button_label="פתח תפריט",
    )


async def send_day_availability_buttons(to: str, day_name: str, day_date: date, week_start: date, week_end: date, step: int, total: int) -> None:
    body = (
        f"📅 *זמינות שבוע {week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}* ({step}/{total})\n\n"
        f"*יום {day_name} {day_date.strftime('%d/%m')}* — מה הזמינות שלך?"
    )
    # Max 3 buttons — send morning/evening/any in first message
    # "לא זמין" as separate action (4th option → use list instead)
    await send_list(
        to=to,
        body=body,
        sections=[{
            "title": "בחר זמינות",
            "rows": [
                {"id": "avail_morning", "title": "🌅 בוקר",       "description": "זמין/ה למשמרת בוקר"},
                {"id": "avail_evening", "title": "🌙 ערב",         "description": "זמין/ה למשמרת ערב"},
                {"id": "avail_any",     "title": "☀️ כל משמרת",   "description": "זמין/ה לכל שעה"},
                {"id": "avail_none",    "title": "❌ לא זמין/ה",   "description": "לא זמין/ה ביום זה"},
            ],
        }],
        button_label="בחר זמינות",
    )


# ── DB helpers (same as Twilio version) ────────────────────────────────────────

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
    result = await db.execute(select(Employee).where(Employee.is_active == True))
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


def next_week_sunday() -> date:
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    return today + timedelta(days=days_until_sunday)


# ── Commands ────────────────────────────────────────────────────────────────────

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
    dow = (shift.date.weekday() + 1) % 7
    tmpl = await db.get(ShiftTemplate, shift.template_id) if shift.template_id else None
    name = tmpl.name if tmpl else "משמרת"
    return (
        f"📅 *המשמרת הבאה שלך:*\n"
        f"{name} – יום {DAY_NAMES[dow]} {shift.date.strftime('%d/%m')}\n"
        f"🕐 {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"
    )


async def cmd_week_schedule(employee: Employee, db: AsyncSession) -> str:
    from app.models.scheduled_shift import ScheduledShift
    today = datetime.now(timezone.utc).date()
    dow_today = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=dow_today)
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


async def cmd_hours(employee: Employee, db: AsyncSession) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    now_il = datetime.now(timezone.utc) + timedelta(hours=3)
    month, year = now_il.month, now_il.year
    from_date = date(year, month, 1)
    to_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    result = await db.execute(
        select(Attendance).where(
            and_(Attendance.employee_id == employee.id,
                 Attendance.date >= from_date, Attendance.date < to_date,
                 Attendance.check_out != None)
        )
    )
    records = result.scalars().all()
    if not records:
        return "📊 אין נתוני נוכחות לחודש הנוכחי."
    total_minutes = sum(r.total_minutes or 0 for r in records)
    hours, mins = total_minutes // 60, total_minutes % 60
    month_names = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    pay_line = ""
    if employee.hourly_rate:
        pay = round(employee.hourly_rate * total_minutes / 60, 2)
        pay_line = f"\n💰 שכר לתשלום: *₪{pay:,.2f}*"
    return (
        f"📊 *נוכחות {month_names[month-1]} {year}*\n\n"
        f"📅 ימים עבדת: *{len(records)}*\n"
        f"⏱ סה״כ שעות: *{hours}:{mins:02d}*"
        f"{pay_line}"
    )


async def cmd_checkin(employee: Employee, db: AsyncSession, lat=None, lng=None) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    existing = await db.execute(
        select(Attendance).where(
            and_(Attendance.employee_id == employee.id, Attendance.date == today, Attendance.check_out == None)
        )
    )
    if existing.scalar_one_or_none():
        return "⚠️ כבר רשום/ה כניסה היום.\nשלח *יציאה* כשאתה יוצא."
    org = await db.get(Organization, employee.org_id)
    is_valid, location_msg = True, ""
    if lat is not None and lng is not None and org and org.settings:
        s = org.settings
        biz_lat, biz_lng = s.get("location_lat"), s.get("location_lng")
        radius = s.get("location_radius", 200)
        if biz_lat and biz_lng:
            from math import radians, sin, cos, sqrt, atan2
            R = 6_371_000
            p1, p2 = radians(lat), radians(float(biz_lat))
            dp = radians(float(biz_lat) - lat)
            dl = radians(float(biz_lng) - lng)
            a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
            dist = R * 2 * atan2(sqrt(a), sqrt(1-a))
            is_valid = dist <= float(radius)
            location_msg = f"\n📍 מיקום אומת ✅ ({int(dist)} מ׳)" if is_valid else f"\n⚠️ מיקום לא אומת ({int(dist)} מ׳ מהעסק)"
    import uuid
    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)
    db.add(Attendance(
        id=str(uuid.uuid4()), employee_id=employee.id, org_id=employee.org_id,
        date=today, check_in=now_utc, check_in_lat=lat, check_in_lng=lng, is_valid_location=is_valid,
    ))
    await db.commit()
    return f"🟢 *כניסה נרשמה!*\n⏰ {now_il.strftime('%H:%M')}{location_msg}"


async def cmd_checkout(employee: Employee, db: AsyncSession) -> str:
    from app.models.attendance import Attendance
    from sqlalchemy import and_
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    result = await db.execute(
        select(Attendance).where(
            and_(Attendance.employee_id == employee.id, Attendance.date == today, Attendance.check_out == None)
        )
    )
    att = result.scalar_one_or_none()
    if not att:
        return "⚠️ לא נמצאת רשומת כניסה פתוחה היום.\nשלח *כניסה* כדי להתחיל."
    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)
    total_minutes = int((now_utc - (att.check_in.replace(tzinfo=timezone.utc) if att.check_in.tzinfo is None else att.check_in)).total_seconds() / 60)
    att.check_out = now_utc
    att.total_minutes = total_minutes
    await db.commit()
    hours, mins = total_minutes // 60, total_minutes % 60
    pay_msg = ""
    if employee.hourly_rate:
        pay = round(employee.hourly_rate * total_minutes / 60, 2)
        pay_msg = f"\n💰 שכר היום: ₪{pay:,.2f}"
    return (
        f"🔴 *יציאה נרשמה!*\n"
        f"⏰ {now_il.strftime('%H:%M')}\n"
        f"⏱ עבדת: *{hours}:{mins:02d} שעות*{pay_msg}\n\n"
        f"להתראות! 👋"
    )


async def cmd_cant_come(employee: Employee, db: AsyncSession) -> tuple[str, list[str]]:
    from app.models.scheduled_shift import ScheduledShift
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    week_end = today + timedelta(days=7)
    result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.employee_id == employee.id,
            ScheduledShift.date >= today,
            ScheduledShift.date <= week_end,
            ScheduledShift.status.in_(["assigned", "swap_requested"]),
        ).order_by(ScheduledShift.date, ScheduledShift.start_time)
    )
    shifts = result.scalars().all()
    if not shifts:
        return "😊 אין לך משמרות קרובות שניתן להחליף.", []
    lines = ["🔄 *בקשת החלפת משמרת*\n\nלאיזו משמרת אינך יכול/ה להגיע?"]
    shift_ids = []
    for i, s in enumerate(shifts, 1):
        dow = (s.date.weekday() + 1) % 7
        lines.append(f"{i}. יום {DAY_NAMES[dow]} {s.date.strftime('%d/%m')} {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}")
        shift_ids.append(s.id)
    lines.append("\n_שלח מספר המשמרת_")
    return "\n".join(lines), shift_ids


async def find_and_notify_replacements(shift_id: str, requester_name: str, org_id: str, db: AsyncSession) -> int:
    from app.models.scheduled_shift import ScheduledShift
    shift = await db.get(ScheduledShift, shift_id)
    if not shift:
        return 0
    dow = (shift.date.weekday() + 1) % 7
    shift_display = f"יום {DAY_NAMES[dow]} {shift.date.strftime('%d/%m')} {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"
    result = await db.execute(
        select(Employee).where(Employee.org_id == org_id, Employee.is_active == True,
                               Employee.id != shift.employee_id, Employee.phone != None)
    )
    all_employees = result.scalars().all()
    same_shift_result = await db.execute(
        select(ScheduledShift).where(
            ScheduledShift.date == shift.date, ScheduledShift.start_time == shift.start_time,
            ScheduledShift.status.notin_(["cancelled"]),
        )
    )
    same_shift_ids = {s.employee_id for s in same_shift_result.scalars().all()}
    candidates = [e for e in all_employees if e.id not in same_shift_ids]
    sent = 0
    for candidate in candidates:
        body_text = (
            f"👋 שלום {candidate.name}!\n"
            f"*{requester_name}* מחפש/ת מחליף/ה למשמרת:\n"
            f"📅 {shift_display}\n\n"
            f"האם תוכל/י להחליף?"
        )
        ok = await send_buttons(
            to=candidate.phone,
            body=body_text,
            buttons=[
                {"id": f"swap_yes_{shift_id[:20]}", "title": "✅ אני יכול/ה"},
                {"id": "swap_no", "title": "❌ לא יכול/ה"},
            ],
        )
        if ok:
            sent += 1
            norm_phone = _normalize_phone(candidate.phone)
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
        return "❌ כבר יש לך משמרת באותה שעה, לא ניתן לקחת את המשמרת."
    original_emp = await db.get(Employee, shift.employee_id)
    shift.employee_id = employee.id
    shift.status = "assigned"
    await db.commit()
    if original_emp and original_emp.phone:
        await send_text(original_emp.phone, f"✅ *{employee.name}* יחליף אותך במשמרת:\n{shift_display}")
    managers = await db.execute(
        select(Employee).where(Employee.org_id == employee.org_id,
                               Employee.role.in_(["manager", "owner"]),
                               Employee.is_active == True, Employee.phone != None)
    )
    orig_name = original_emp.name if original_emp else "?"
    for mgr in managers.scalars().all():
        await send_text(mgr.phone, f"🔄 *עדכון סידור*\n{shift_display}\n{orig_name} ← {employee.name}")
    return f"✅ *אושר!* קיבלת את המשמרת:\n{shift_display}"


async def save_availability(employee: Employee, week_start: date, operating_days: list[int], responses: dict, db: AsyncSession) -> str:
    week_end = week_start + timedelta(days=6)
    week_result = await db.execute(
        select(ScheduleWeek).where(ScheduleWeek.org_id == employee.org_id, ScheduleWeek.week_start == week_start)
    )
    week = week_result.scalar_one_or_none()
    if not week:
        import uuid
        week = ScheduleWeek(id=str(uuid.uuid4()), org_id=employee.org_id,
                             week_start=week_start, week_end=week_end, status="collecting")
        db.add(week)
        await db.flush()
    sub_result = await db.execute(
        select(AvailabilitySubmission).where(
            AvailabilitySubmission.employee_id == employee.id,
            AvailabilitySubmission.week_id == week.id,
        )
    )
    sub = sub_result.scalar_one_or_none()
    day_prefs = {
        str(day_idx): {"available": responses[str(day_idx)]["available"],
                       "preferred_types": responses[str(day_idx)].get("preferred_types", []),
                       "is_hard": responses[str(day_idx)].get("is_hard", False)}
        for day_idx in operating_days if str(day_idx) in responses
    }
    if sub:
        from sqlalchemy import delete
        await db.execute(delete(UnavailabilitySlot).where(UnavailabilitySlot.submission_id == sub.id))
        sub.day_preferences = day_prefs
    else:
        import uuid
        sub = AvailabilitySubmission(id=str(uuid.uuid4()), employee_id=employee.id,
                                      week_id=week.id, day_preferences=day_prefs)
        db.add(sub)
        await db.flush()
    for day_idx in operating_days:
        resp = responses.get(str(day_idx))
        if not resp or resp["available"]:
            continue
        import uuid
        db.add(UnavailabilitySlot(id=str(uuid.uuid4()), submission_id=sub.id,
                                   date=week_start + timedelta(days=day_idx),
                                   is_hard_constraint=resp.get("is_hard", False)))
    await db.commit()
    return f"✅ *הזמינות נשמרה לשבוע {week_start.strftime('%d/%m')}!*\nתודה {employee.name} 🙏"


def build_availability_summary(responses: dict, operating_days: list[int], week_start: date) -> str:
    lines = [f"📋 *סיכום זמינות שבוע {week_start.strftime('%d/%m')}:*"]
    for day_idx in operating_days:
        resp = responses.get(str(day_idx))
        label = resp.get("label", "?") if resp else "זמין לכל"
        lines.append(f"• {DAY_NAMES[day_idx]}: {label}")
    lines.append("")
    return "\n".join(lines)


# ── Webhook ─────────────────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta webhook verification (one-time setup)."""
    params = dict(request.query_params)
    verify_token = os.getenv("WHATSAPP_META_VERIFY_TOKEN", "shiftwise_verify")
    if (params.get("hub.mode") == "subscribe" and
            params.get("hub.verify_token") == verify_token):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()

    # Extract message from Meta's nested format
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]["value"]
    except (KeyError, IndexError):
        return {"status": "ok"}

    # Ignore status updates (delivered, read)
    if "messages" not in changes:
        return {"status": "ok"}

    message = changes["messages"][0]
    raw_phone = message.get("from", "")
    msg_type = message.get("type", "")

    # Normalize phone: Meta sends without +, e.g. 972501234567
    phone = raw_phone  # already in 972XXXXXXXXX format from Meta

    # Extract text / button / list / location
    text_body = ""
    button_id = ""
    lat, lng = None, None

    if msg_type == "text":
        text_body = message.get("text", {}).get("body", "").strip()
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        itype = interactive.get("type", "")
        if itype == "button_reply":
            button_id = interactive["button_reply"]["id"]
            text_body = interactive["button_reply"]["title"]
        elif itype == "list_reply":
            button_id = interactive["list_reply"]["id"]
            text_body = interactive["list_reply"]["title"]
    elif msg_type == "location":
        lat = message["location"].get("latitude")
        lng = message["location"].get("longitude")

    employee = await find_employee(phone, db)
    if not employee:
        await send_text(phone, "❌ מספר הטלפון שלך לא מזוהה במערכת.\nפנה למנהל שלך לחיבור הטלפון לחשבון.")
        return {"status": "ok"}

    session = await get_session(phone, db)

    # Auto-expire sessions older than 15 min
    if session.updated_at:
        age = (datetime.now(timezone.utc) - session.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
        if age > 900 and session.state != "idle":
            session.state = "idle"
            session.context = {}
            await db.commit()

    normalized = text_body.lower().strip()

    # ── Location shared ──
    if lat is not None and lng is not None:
        if session.state == "checkin_waiting_location":
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            msg = await cmd_checkin(employee, db, lat=lat, lng=lng)
            await send_text(phone, msg)
        else:
            # Location shared while idle → check-in
            msg = await cmd_checkin(employee, db, lat=lat, lng=lng)
            await send_text(phone, msg)
        return {"status": "ok"}

    # ── Global cancel ──
    if normalized in ("ביטול", "cancel", "בטל") or button_id == "cancel":
        session.state = "idle"
        session.context = {}
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await send_text(phone, "❌ הפעולה בוטלה.")
        await send_main_menu(phone)
        return {"status": "ok"}

    # ── Menu / greeting ──
    if (not button_id and any(kw in normalized for kw in ["שלום", "היי", "תפריט", "עזרה", "menu", "help", "hello", "hi"])
            or button_id == "menu"):
        await send_main_menu(phone)
        return {"status": "ok"}

    # ── Button: check-in ──
    if button_id == "checkin" or any(kw in normalized for kw in ["כניסה", "נכנסתי", "הגעתי"]):
        org = await db.get(Organization, employee.org_id)
        has_location = org and org.settings and org.settings.get("location_lat")
        if has_location:
            session.state = "checkin_waiting_location"
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await send_buttons(
                to=phone,
                body="📍 *כניסה לעבודה*\n\nלאימות מיקום — שתף את המיקום שלך\nלחץ 📎 ← מיקום ← שלח מיקום נוכחי",
                buttons=[{"id": "checkin_no_location", "title": "⚡ כניסה ללא מיקום"}],
            )
        else:
            msg = await cmd_checkin(employee, db)
            await send_text(phone, msg)
        return {"status": "ok"}

    if button_id == "checkin_no_location":
        session.state = "idle"
        session.context = {}
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        msg = await cmd_checkin(employee, db)
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── Button: check-out ──
    if button_id == "checkout" or any(kw in normalized for kw in ["יציאה", "יצאתי", "סיימתי"]):
        msg = await cmd_checkout(employee, db)
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── Button: hours ──
    if button_id == "hours" or any(kw in normalized for kw in ["שעות", "שכר", "נוכחות"]):
        msg = await cmd_hours(employee, db)
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── Button: next shift ──
    if button_id == "next_shift" or any(kw in normalized for kw in ["משמרת", "הבא"]):
        msg = await cmd_next_shift(employee, db)
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── Button: week schedule ──
    if button_id == "week_schedule" or any(kw in normalized for kw in ["סידור", "שבוע"]):
        msg = await cmd_week_schedule(employee, db)
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── Button: availability ──
    if button_id == "availability" or "זמינות" in normalized:
        week_start = next_week_sunday()
        operating_days = await get_org_operating_days(employee.org_id, db)
        if not operating_days:
            await send_text(phone, "⚠️ לא הוגדרו ימי פעילות. פנה למנהל.")
            return {"status": "ok"}
        week_end = week_start + timedelta(days=6)
        first_day_idx = operating_days[0]
        first_date = week_start + timedelta(days=first_day_idx)
        session.state = "availability_day_by_day"
        session.context = {"week_start": week_start.isoformat(), "operating_days": operating_days, "responses": {}, "step": 0}
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await send_day_availability_buttons(phone, DAY_NAMES[first_day_idx], first_date, week_start, week_end, 1, len(operating_days))
        return {"status": "ok"}

    # ── Button: cant come ──
    if button_id == "cant_come" or any(kw in normalized for kw in ["לא יכול", "החלפה"]):
        msg, shift_ids = await cmd_cant_come(employee, db)
        if shift_ids:
            session.state = "cant_come_selecting"
            session.context = {"shift_ids": shift_ids}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
        await send_text(phone, msg)
        return {"status": "ok"}

    # ── State: availability day-by-day ──
    if session.state == "availability_day_by_day":
        ctx = dict(session.context or {})
        operating_days: list[int] = ctx.get("operating_days", [0, 1, 2, 3, 4, 5])
        week_start = date.fromisoformat(ctx.get("week_start", ""))
        week_end = week_start + timedelta(days=6)
        responses: dict = ctx.get("responses", {})
        step: int = ctx.get("step", 0)

        option = OPTION_MAP.get(button_id) or OPTION_MAP.get(normalized) or OPTION_MAP.get(text_body.strip())
        if not option:
            current_day_idx = operating_days[step]
            current_date = week_start + timedelta(days=current_day_idx)
            await send_text(phone, "⚠️ לא הבנתי, בחר/י מהרשימה 👇")
            await send_day_availability_buttons(phone, DAY_NAMES[current_day_idx], current_date, week_start, week_end, step + 1, len(operating_days))
            return {"status": "ok"}

        current_day_idx = operating_days[step]
        responses[str(current_day_idx)] = option
        step += 1

        if step < len(operating_days):
            next_day_idx = operating_days[step]
            next_date = week_start + timedelta(days=next_day_idx)
            ctx.update({"responses": responses, "step": step})
            session.context = ctx
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await send_day_availability_buttons(phone, DAY_NAMES[next_day_idx], next_date, week_start, week_end, step + 1, len(operating_days))
            return {"status": "ok"}

        # All days done → confirm
        ctx.update({"responses": responses})
        session.state = "availability_confirm"
        session.context = ctx
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        summary = build_availability_summary(responses, operating_days, week_start)
        await send_buttons(
            to=phone,
            body=summary + "לאשר ולשמור?",
            buttons=[{"id": "avail_confirm_yes", "title": "✅ אשר ושמור"}, {"id": "avail_confirm_no", "title": "❌ בטל"}],
        )
        return {"status": "ok"}

    # ── State: availability confirm ──
    if session.state == "availability_confirm":
        ctx = dict(session.context or {})
        if button_id in ("avail_confirm_yes",) or normalized in ("כן", "yes", "אישור"):
            week_start = date.fromisoformat(ctx["week_start"])
            operating_days = ctx.get("operating_days", [0, 1, 2, 3, 4, 5])
            responses = ctx.get("responses", {})
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            msg = await save_availability(employee, week_start, operating_days, responses, db)
            await send_text(phone, msg)
        else:
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await send_text(phone, "❌ הזמינות לא נשמרה.")
            await send_main_menu(phone)
        return {"status": "ok"}

    # ── State: cant_come selecting ──
    if session.state == "cant_come_selecting":
        ctx = dict(session.context or {})
        shift_ids: list[str] = ctx.get("shift_ids", [])
        try:
            idx = int(text_body.strip()) - 1
            if idx < 0 or idx >= len(shift_ids):
                raise ValueError()
        except (ValueError, TypeError):
            await send_text(phone, f"⚠️ שלח מספר בין 1 ל-{len(shift_ids)}.")
            return {"status": "ok"}
        from app.models.scheduled_shift import ScheduledShift
        shift = await db.get(ScheduledShift, shift_ids[idx])
        if not shift:
            session.state = "idle"
            session.context = {}
            await db.commit()
            await send_text(phone, "❌ המשמרת לא נמצאה.")
            return {"status": "ok"}
        dow = (shift.date.weekday() + 1) % 7
        shift_display = f"יום {DAY_NAMES[dow]} {shift.date.strftime('%d/%m')} {shift.start_time.strftime('%H:%M')}–{shift.end_time.strftime('%H:%M')}"
        ctx.update({"selected_shift_id": shift.id, "selected_shift_display": shift_display})
        session.state = "cant_come_confirm"
        session.context = ctx
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await send_buttons(
            to=phone,
            body=f"🔄 *אישור בקשת החלפה*\n\n📅 {shift_display}\n\nלאשר ולשלוח לעובדים?",
            buttons=[{"id": "swap_confirm_yes", "title": "✅ כן, שלח בקשה"}, {"id": "swap_confirm_no", "title": "❌ בטל"}],
        )
        return {"status": "ok"}

    # ── State: cant_come confirm ──
    if session.state == "cant_come_confirm":
        ctx = dict(session.context or {})
        if button_id == "swap_confirm_yes" or normalized in ("כן", "yes"):
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
                await send_text(phone, f"✅ הבקשה נשלחה ל-{sent} עובדים!\n📅 {shift_display}\n\nתקבל/י עדכון כשמישהו יאשר.")
            else:
                await send_text(phone, "⚠️ לא נמצאו עובדים זמינים. פנה/י ישירות למנהל.")
        else:
            session.state = "idle"
            session.context = {}
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await send_text(phone, "❌ הבקשה בוטלה.")
        return {"status": "ok"}

    # ── Swap offer response ──
    if button_id.startswith("swap_yes_"):
        ctx = dict(session.context or {})
        if "pending_swap_shift_id" in ctx:
            result_msg = await handle_volunteer_acceptance(employee, ctx, db)
            ctx.pop("pending_swap_shift_id", None)
            ctx.pop("pending_swap_display", None)
            ctx.pop("pending_swap_requester", None)
            session.context = ctx
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await send_text(phone, result_msg)
        return {"status": "ok"}

    if button_id == "swap_no":
        ctx = dict(session.context or {})
        ctx.pop("pending_swap_shift_id", None)
        ctx.pop("pending_swap_display", None)
        ctx.pop("pending_swap_requester", None)
        session.context = ctx
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await send_text(phone, "הובן, תודה על התגובה.")
        return {"status": "ok"}

    # Fallback → main menu
    await send_main_menu(phone)
    return {"status": "ok"}
