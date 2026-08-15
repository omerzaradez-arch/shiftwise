"""
Transactional email via Resend.

Used for anything that shouldn't travel over WhatsApp — passwords above all.
WhatsApp templates are readable by anyone holding the phone and sit in a chat
log forever; email at least lands in an account the person controls separately.

Env:
    RESEND_API_KEY = re_...            (from resend.com/api-keys)
    RESEND_FROM    = ShiftWise <no-reply@yourdomain.com>

RESEND_FROM must use a domain verified in Resend, otherwise the API rejects the
send. Everything here degrades to False + a log line rather than raising, so a
missing key never breaks the request that triggered it.
"""

import os
import httpx


def is_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip())


def mask_email(address: str) -> str:
    """d***@gmail.com — enough to recognise your own inbox, not enough to learn it."""
    if not address or "@" not in address:
        return ""
    local, _, domain = address.partition("@")
    head = local[0] if local else ""
    return f"{head}***@{domain}"


async def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = os.getenv("RESEND_FROM", "").strip()
    if not api_key or not sender:
        print("[mail] RESEND_API_KEY or RESEND_FROM missing — email not sent", flush=True)
        return False

    payload: dict = {"from": sender, "to": [to], "subject": subject, "html": html}
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json=payload,
                timeout=10.0,
            )
            if resp.status_code not in (200, 201):
                print(f"[mail] ERROR {resp.status_code}: {resp.text[:200]}", flush=True)
                return False
            print(f"[mail] sent to {mask_email(to)} — {subject}", flush=True)
            return True
    except Exception as e:
        print(f"[mail] exception: {e}", flush=True)
        return False


def _shell(title: str, body_html: str) -> str:
    """Minimal RTL Hebrew email shell. Inline styles only — mail clients strip <style>."""
    return f"""\
<div dir="rtl" style="margin:0;padding:24px;background:#f4f5f2;font-family:Segoe UI,Arial,sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e0e3dc;padding:28px 26px">
    <p style="margin:0 0 18px;font-size:13px;letter-spacing:.08em;color:#1E6F52;font-weight:700">SHIFTWISE</p>
    <h1 style="margin:0 0 16px;font-size:21px;color:#16201C;font-weight:700">{title}</h1>
    {body_html}
  </div>
</div>"""


async def send_password_reset(to: str, name: str, new_password: str) -> bool:
    body = f"""\
    <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#46534C">
      שלום {name}, ביקשת לאפס את הסיסמה שלך ל-ShiftWise.
    </p>
    <p style="margin:0 0 6px;font-size:13px;color:#6E7B73">הסיסמה החדשה שלך</p>
    <p style="margin:0 0 18px;padding:12px 16px;background:#f2f3ef;border:1px solid #e0e3dc;
              font-family:Consolas,monospace;font-size:19px;font-weight:700;
              letter-spacing:.06em;color:#16201C;direction:ltr;text-align:center">{new_password}</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#46534C">
      אחרי הכניסה תוכל/י להחליף אותה לסיסמה משלך במסך ההגדרות.
    </p>
    <p style="margin:0;font-size:14px;line-height:1.7;color:#8A5D0E">
      אם לא ביקשת לאפס את הסיסמה — מישהו ניסה להיכנס לחשבון שלך. צור/צרי איתנו קשר מיד.
    </p>"""
    plain = (
        f"שלום {name}, ביקשת לאפס את הסיסמה שלך ל-ShiftWise.\n\n"
        f"הסיסמה החדשה שלך: {new_password}\n\n"
        "אחרי הכניסה תוכל/י להחליף אותה במסך ההגדרות.\n"
        "אם לא ביקשת את האיפוס — פנה/י אלינו מיד."
    )
    return await send_email(to, "איפוס סיסמה ל-ShiftWise", _shell("איפוס סיסמה", body), plain)
