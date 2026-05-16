"""
Web Push helper using VAPID + pywebpush.

Env vars:
- VAPID_PUBLIC_KEY: base64 URL-safe public key
- VAPID_PRIVATE_KEY: base64 URL-safe private key
- VAPID_CONTACT_EMAIL: mailto: address (e.g. mailto:admin@example.com)

Generate keys once (in Python REPL):
    from py_vapid import Vapid
    v = Vapid()
    v.generate_keys()
    print("PUBLIC :", v.public_key.public_bytes(encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint).hex())
    # or use: py-vapid --gen
"""

import os
import json
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PushSubscription


def _vapid_claims() -> dict:
    return {
        "sub": os.getenv("VAPID_CONTACT_EMAIL", "mailto:admin@shiftwise.app"),
    }


async def send_push_to_user(
    employee_id: str,
    title: str,
    body: str,
    url: str = "/",
    db: AsyncSession | None = None,
) -> int:
    """
    Sends a push notification to all subscriptions of one employee.
    Returns number of successful pushes.
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("[push] pywebpush not installed — skipping", flush=True)
        return 0

    vapid_private = os.getenv("VAPID_PRIVATE_KEY", "")
    if not vapid_private:
        print("[push] VAPID_PRIVATE_KEY not set — skipping", flush=True)
        return 0

    # Get DB session if not provided
    own_session = False
    if db is None:
        from app.database import async_session_factory
        db = async_session_factory()
        own_session = True

    try:
        result = await db.execute(
            select(PushSubscription).where(PushSubscription.employee_id == employee_id)
        )
        subs = result.scalars().all()
        if not subs:
            return 0

        sent = 0
        payload = json.dumps({"title": title, "body": body, "url": url})

        for sub in subs:
            subscription_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                # webpush is synchronous — run in threadpool
                await asyncio.to_thread(
                    webpush,
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims=_vapid_claims(),
                )
                sub.last_used_at = datetime.now(timezone.utc)
                sent += 1
            except WebPushException as e:
                print(f"[push] WebPushException: {e}", flush=True)
                # 410 Gone → subscription dead, remove it
                if e.response is not None and e.response.status_code in (404, 410):
                    await db.delete(sub)
            except Exception as e:
                print(f"[push] exception: {e}", flush=True)

        await db.commit()
        return sent
    finally:
        if own_session:
            await db.close()


async def send_push_to_managers(org_id: str, title: str, body: str, url: str = "/") -> int:
    """Send push notification to all managers/owners of an org."""
    from app.database import async_session_factory
    from app.models import Employee

    async with async_session_factory() as db:
        result = await db.execute(
            select(Employee).where(
                Employee.org_id == org_id,
                Employee.role.in_(["manager", "owner"]),
                Employee.is_active == True,
            )
        )
        managers = result.scalars().all()

    total_sent = 0
    for mgr in managers:
        total_sent += await send_push_to_user(mgr.id, title, body, url)
    return total_sent
