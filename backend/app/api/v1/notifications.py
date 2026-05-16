"""
Push notification subscription endpoints.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel

from app.database import get_db
from app.models import PushSubscription, Employee
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Returns the VAPID public key for the frontend to subscribe."""
    return {"key": os.getenv("VAPID_PUBLIC_KEY", "")}


@router.get("/debug")
async def debug_vapid():
    """Debug — check if VAPID env vars are set correctly."""
    pub = os.getenv("VAPID_PUBLIC_KEY", "")
    priv = os.getenv("VAPID_PRIVATE_KEY", "")
    email = os.getenv("VAPID_CONTACT_EMAIL", "")
    return {
        "VAPID_PUBLIC_KEY_set": bool(pub),
        "VAPID_PUBLIC_KEY_length": len(pub),
        "VAPID_PUBLIC_KEY_preview": pub[:20] + "..." if pub else "(empty)",
        "VAPID_PRIVATE_KEY_set": bool(priv),
        "VAPID_PRIVATE_KEY_length": len(priv),
        "VAPID_PRIVATE_KEY_starts_with_BEGIN": priv.strip().startswith("-----BEGIN") if priv else False,
        "VAPID_PRIVATE_KEY_ends_with_END": priv.strip().endswith("-----") if priv else False,
        "VAPID_PRIVATE_KEY_has_newlines": "\n" in priv,
        "VAPID_CONTACT_EMAIL": email or "(empty)",
    }


class SubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.post("/subscribe")
async def subscribe(
    data: SubscribeRequest,
    request: Request,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a push subscription for the current user."""
    # Remove duplicate
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.employee_id == current_user.id,
            PushSubscription.endpoint == data.endpoint,
        )
    )
    sub = PushSubscription(
        employee_id=current_user.id,
        endpoint=data.endpoint,
        p256dh=data.p256dh,
        auth=data.auth,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(sub)
    await db.commit()
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(
    data: dict,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a subscription by endpoint."""
    endpoint = data.get("endpoint", "")
    if endpoint:
        await db.execute(
            delete(PushSubscription).where(
                PushSubscription.employee_id == current_user.id,
                PushSubscription.endpoint == endpoint,
            )
        )
        await db.commit()
    return {"ok": True}


@router.post("/test")
async def test_push(
    current_user: Employee = Depends(get_current_user),
):
    """Send a test push to the current user."""
    from app.core.push import send_push_to_user
    sent = await send_push_to_user(
        employee_id=current_user.id,
        title="🔔 בדיקה — ShiftWise",
        body="התראות Push עובדות מצוין! 🎉",
        url="/schedule",
    )
    return {"ok": True, "sent": sent}
