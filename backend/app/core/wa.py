"""
Provider-agnostic WhatsApp sending layer.

Everything outside the two webhook modules (whatsapp.py = Twilio,
whatsapp_meta.py = Meta Cloud API) sends through here, so switching providers
is one env var and never a code change:

    WHATSAPP_PROVIDER = meta | twilio      (default: meta)

Proactive messages (scheduler jobs) are special on Meta: outside the 24-hour
customer-service window only *pre-approved templates* may be sent. Each
proactive helper below therefore tries its template first and falls back to a
free-form interactive message, which still works inside the window and during
local testing. Template names come from env so they can be wired up the moment
Meta approves them:

    WHATSAPP_TEMPLATE_SHIFT_START   (e.g. shift_start_reminder)
    WHATSAPP_TEMPLATE_SHIFT_LATE    (e.g. shift_late_alert)
    WHATSAPP_TEMPLATE_AVAILABILITY  (e.g. availability_kickoff)
    WHATSAPP_TEMPLATE_LANG          (default: he)
"""

import os
from datetime import date


def provider() -> str:
    return os.getenv("WHATSAPP_PROVIDER", "meta").strip().lower()


def is_meta() -> bool:
    return provider() != "twilio"


# ── Generic sends ───────────────────────────────────────────────────────────────

async def send_text(phone: str, body: str, media_url: str | None = None) -> bool:
    if is_meta():
        from app.api.v1 import whatsapp_meta as meta
        if media_url:
            print("[wa] media_url ignored on Meta provider", flush=True)
        return await meta.send_text(phone, body)
    from app.api.v1.whatsapp import send_whatsapp_to
    return await send_whatsapp_to(phone, body, media_url)


# Back-compat alias — the Twilio-era name used across the codebase.
send_whatsapp_to = send_text


async def send_buttons(phone: str, body: str, buttons: list[dict]) -> bool:
    """buttons = [{"id": ..., "title": ...}, ...] (max 3)."""
    if is_meta():
        from app.api.v1 import whatsapp_meta as meta
        return await meta.send_buttons(phone, body, buttons)

    import uuid
    from app.api.v1.whatsapp import _twilio_send_interactive
    return await _twilio_send_interactive(phone, {
        "friendly_name": f"sw_btn_{uuid.uuid4().hex[:8]}",
        "language": "he",
        "types": {
            "twilio/quick-reply": {
                "body": body,
                "actions": [{"title": b["title"][:20], "id": b["id"]} for b in buttons[:3]],
            }
        },
    })


async def send_template(
    phone: str,
    name: str,
    body_params: list[str] | None = None,
    button_payloads: list[str] | None = None,
) -> bool:
    """Meta-only. Returns False on Twilio so callers fall back cleanly."""
    if not is_meta():
        return False
    from app.api.v1 import whatsapp_meta as meta
    return await meta.send_template(phone, name, body_params, button_payloads)


# ── Proactive messages (scheduler jobs) ─────────────────────────────────────────

async def notify_shift_start(phone: str, name: str, start_str: str) -> bool:
    """'Your shift just started — did you clock in?' with a check-in button."""
    template = os.getenv("WHATSAPP_TEMPLATE_SHIFT_START", "").strip()
    if template and await send_template(
        phone, template, [name, start_str], ["checkin", "start_later"]
    ):
        return True

    body = (
        f"היי {name}! 👋\n\n"
        f"יש לך משמרת עכשיו ({start_str}).\n"
        f"תעדכן אותי אם התחלת:"
    )
    if await send_buttons(phone, body, [
        {"id": "checkin", "title": "✅ התחלתי"},
        {"id": "start_later", "title": "⏳ עוד לא"},
    ]):
        return True
    return await send_text(phone, body + "\n\nשלח *כניסה* כשהתחלת.")


async def notify_shift_late(phone: str, name: str, start_str: str) -> bool:
    """Late reminder for an employee who never checked in."""
    template = os.getenv("WHATSAPP_TEMPLATE_SHIFT_LATE", "").strip()
    if template and await send_template(
        phone, template, [name, start_str], ["checkin", "cant_come"]
    ):
        return True

    body = (
        f"⏰ שלום {name}!\n\n"
        f"המשמרת שלך התחילה בשעה *{start_str}* ועדיין לא דיווחת כניסה."
    )
    if await send_buttons(phone, body, [
        {"id": "checkin", "title": "🟢 הגעתי"},
        {"id": "cant_come", "title": "🔄 לא יכול להגיע"},
    ]):
        return True
    return await send_text(
        phone,
        body + "\n\nשלח *כניסה* אם הגעת לעבודה 🟢\nשלח *לא יכול* אם אינך יכול להגיע 🔄",
    )


async def notify_schedule_published(
    phone: str, name: str, week_range: str, status_text: str, fallback_body: str
) -> bool:
    """Schedule-published announcement.

    The employee's own shift list can't ride along as a template parameter —
    Meta rejects parameters containing newlines — so the template carries a
    button instead, and tapping it opens the 24h window for the full list.
    """
    template = os.getenv("WHATSAPP_TEMPLATE_SCHEDULE_PUBLISHED", "").strip()
    if template and await send_template(
        phone, template, [name, week_range, status_text], ["week_schedule"]
    ):
        return True
    return await send_text(phone, fallback_body)


async def notify_swap_request(
    phone: str, candidate_name: str, requester_name: str, shift_display: str
) -> bool:
    """Offer an open shift to a candidate replacement."""
    template = os.getenv("WHATSAPP_TEMPLATE_SWAP_REQUEST", "").strip()
    if template and await send_template(
        phone, template,
        [candidate_name, requester_name, shift_display],
        ["swap_yes_confirm", "swap_no"],
    ):
        return True

    body = (
        f"👋 שלום {candidate_name}!\n"
        f"*{requester_name}* מחפש/ת מחליף/ה למשמרת:\n"
        f"📅 {shift_display}\n\n"
        f"האם תוכל/י להחליף?"
    )
    return await send_buttons(phone, body, [
        {"id": "swap_yes_confirm", "title": "✅ אני יכול/ה"},
        {"id": "swap_no", "title": "❌ לא מתאים לי"},
    ])


async def notify_swap_accepted(
    phone: str, name: str, replacement_name: str, shift_display: str, fallback_body: str
) -> bool:
    """Tell the original employee that someone took their shift."""
    template = os.getenv("WHATSAPP_TEMPLATE_SWAP_ACCEPTED", "").strip()
    if template and await send_template(
        phone, template, [name, replacement_name, shift_display]
    ):
        return True
    return await send_text(phone, fallback_body)


async def notify_password_reset(
    phone: str, name: str, masked_email: str, fallback_body: str
) -> bool:
    """Tell a manager their password was reset — without carrying the password.

    The secret travels by email; WhatsApp only says to go look. That keeps this
    template in the UTILITY category: the moment a password or code appears in
    the body, Meta reclassifies it as AUTHENTICATION, which forbids custom
    wording and demands a copy-code button.
    """
    template = os.getenv("WHATSAPP_TEMPLATE_PASSWORD_RESET", "").strip()
    if template and await send_template(phone, template, [name, masked_email]):
        return True
    return await send_text(phone, fallback_body)


async def notify_admin_new_registration(
    phone: str, org_name: str, contact_name: str, contact_phone: str,
    code: str, fallback_body: str,
) -> bool:
    """Tell the ShiftWise admin a business asked to join.

    The activation code stays out of the template on purpose: Meta rejected the
    version carrying it, reading a code in the body as an authentication
    message. The template points the admin at the panel; the free-form fallback,
    which only goes out inside the 24h window, still carries the code.
    """
    template = os.getenv("WHATSAPP_TEMPLATE_ADMIN_REGISTRATION", "").strip()
    if template and await send_template(
        phone, template, [org_name, contact_name, contact_phone]
    ):
        return True
    return await send_text(phone, fallback_body)


async def request_availability(phone: str, name: str, week_start: date, week_end: date) -> bool:
    """Weekly availability kickoff.

    Returns True if a *template* went out — the employee taps its button and the
    webhook starts the day-by-day flow itself, so the caller must NOT pre-seed
    the session. Returns False if no template was sent, meaning the caller
    should seed the session and push the first day question directly.
    """
    template = os.getenv("WHATSAPP_TEMPLATE_AVAILABILITY", "").strip()
    if not template:
        return False
    week_range = f"{week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m')}"
    return await send_template(phone, template, [name, week_range], ["availability"])
