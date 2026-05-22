"""
Background alert jobs — runs on a schedule via APScheduler.
Jobs:
  - shift_start_notify: every 5 min — sends start-of-shift WhatsApp with quick-reply buttons
  - checkin_alert: every 5 min — late reminder for employees who missed check-in
  - availability_request: Mon/Tue/Wed 09:00 IL — kicks off weekly availability flow for employees who haven't submitted
"""

import os
from datetime import datetime, timedelta, timezone, time as dtime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


def _checkin_url(token: str) -> str:
    base = os.getenv("FRONTEND_URL", "https://shiftwise-production.up.railway.app").rstrip("/")
    return f"{base}/checkin/{token}"


async def shift_start_notify_job():
    """
    Every 5 minutes:
    Find shifts that started in the last 5 minutes and haven't been notified yet.
    Send a WhatsApp quick-reply with "התחלתי" / "עוד לא התחלתי".
    """
    from app.models.scheduled_shift import ScheduledShift
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from app.api.v1.whatsapp import send_interactive_confirm, send_whatsapp_to
    from app.api.v1.auth import create_checkin_token

    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)
    today = now_il.date()
    window_start = (now_il - timedelta(minutes=5)).time()
    window_end = now_il.time()

    if window_start > window_end:
        return

    async with async_session_factory() as db:
        shifts = (await db.execute(
            select(ScheduledShift).where(and_(
                ScheduledShift.date == today,
                ScheduledShift.start_time >= window_start,
                ScheduledShift.start_time <= window_end,
                ScheduledShift.status.notin_(["cancelled"]),
                ScheduledShift.checkin_notified == False,
            ))
        )).scalars().all()

        if not shifts:
            return

        print(f"[start_notify] {len(shifts)} shifts starting now", flush=True)

        for shift in shifts:
            # Skip if already checked in
            existing = (await db.execute(
                select(Attendance).where(and_(
                    Attendance.employee_id == shift.employee_id,
                    Attendance.date == today,
                ))
            )).scalar_one_or_none()
            if existing:
                shift.checkin_notified = True
                continue

            emp = await db.get(Employee, shift.employee_id)
            if not emp or not emp.phone or not emp.is_active:
                shift.checkin_notified = True
                continue

            token = create_checkin_token(shift.id, emp.id)
            url = _checkin_url(token)
            start_str = shift.start_time.strftime("%H:%M")

            # Try interactive buttons; fall back to plain message with the link
            body = (
                f"היי {emp.name}! 👋\n\n"
                f"יש לך משמרת עכשיו ({start_str}).\n"
                f"תעדכן אותי אם התחלת:"
            )
            sent = await send_interactive_confirm_with_link(emp.phone, body, url)
            if not sent:
                # Fallback plain message
                fallback = (
                    f"היי {emp.name}! 👋\n\n"
                    f"יש לך משמרת עכשיו ({start_str}).\n"
                    f"לאישור הגעה — לחץ כאן:\n{url}"
                )
                await send_whatsapp_to(emp.phone, fallback)

            shift.checkin_notified = True
            print(f"[start_notify] sent to {emp.name} ({emp.phone}) shift={start_str}", flush=True)

        await db.commit()


async def send_interactive_confirm_with_link(phone: str, body: str, url: str) -> bool:
    """Quick-reply with two buttons; the 'התחלתי' answer routes to the GPS link."""
    from app.api.v1.whatsapp import _twilio_send_interactive
    import uuid
    payload = {
        "friendly_name": f"sw_start_{uuid.uuid4().hex[:8]}",
        "language": "he",
        "types": {
            "twilio/quick-reply": {
                "body": body,
                "actions": [
                    {"title": "התחלתי", "id": "התחלתי"},
                    {"title": "עוד לא", "id": "עוד לא"},
                ],
            }
        },
    }
    return await _twilio_send_interactive(phone, payload)


async def checkin_alert_job():
    """
    Every 5 minutes:
    Find employees with a shift that started 15–45 minutes ago,
    who haven't checked in yet, and haven't been notified yet.
    Send them a WhatsApp reminder.
    """
    from app.models.scheduled_shift import ScheduledShift
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from app.api.v1.whatsapp import send_whatsapp_to

    now_utc = datetime.now(timezone.utc)
    now_il = now_utc + timedelta(hours=3)  # Israel time
    today = now_il.date()

    # Window: shift started between 15 and 45 minutes ago (Israel time)
    # We check every 5 min, window of 30 min → each late shift gets exactly one notification
    window_start = (now_il - timedelta(minutes=45)).time()
    window_end   = (now_il - timedelta(minutes=15)).time()

    # Edge case: window spans midnight — skip (rare and complex)
    if window_start > window_end:
        return

    print(f"[alerts] checkin check — window {window_start.strftime('%H:%M')}–{window_end.strftime('%H:%M')} IL", flush=True)

    async with async_session_factory() as db:
        # Get shifts that started in the window, today, not cancelled
        shifts_result = await db.execute(
            select(ScheduledShift).where(
                and_(
                    ScheduledShift.date == today,
                    ScheduledShift.start_time >= window_start,
                    ScheduledShift.start_time <= window_end,
                    ScheduledShift.status.notin_(["cancelled"]),
                    ScheduledShift.checkin_notified == False,
                )
            )
        )
        shifts = shifts_result.scalars().all()

        if not shifts:
            return

        print(f"[alerts] {len(shifts)} shifts in window", flush=True)

        for shift in shifts:
            # Check if employee already checked in today
            att_result = await db.execute(
                select(Attendance).where(
                    and_(
                        Attendance.employee_id == shift.employee_id,
                        Attendance.date == today,
                    )
                )
            )
            if att_result.scalar_one_or_none():
                # Already checked in — just mark as notified so we skip next time
                shift.checkin_notified = True
                continue

            # Get employee
            emp = await db.get(Employee, shift.employee_id)
            if not emp or not emp.phone or not emp.is_active:
                shift.checkin_notified = True
                continue

            # Send WhatsApp
            start_str = shift.start_time.strftime("%H:%M")
            msg = (
                f"⏰ שלום {emp.name}!\n\n"
                f"המשמרת שלך התחילה בשעה *{start_str}* ועדיין לא דיווחת כניסה.\n\n"
                f"שלח *כניסה* אם הגעת לעבודה 🟢\n"
                f"שלח *לא יכול* אם אינך יכול להגיע 🔄"
            )
            ok = await send_whatsapp_to(emp.phone, msg)
            shift.checkin_notified = True
            print(f"[alerts] notified {emp.name} ({emp.phone}) shift={start_str} sent={ok}", flush=True)

            # Push notify managers too
            try:
                from app.core.push import send_push_to_managers
                await send_push_to_managers(
                    org_id=emp.org_id,
                    title="⚠️ עובד לא דיווח כניסה",
                    body=f"{emp.name} — משמרת {start_str} התחילה ולא דווחה כניסה",
                    url="/payroll",
                )
            except Exception as e:
                print(f"[push] mgr notify failed: {e}", flush=True)

        await db.commit()


async def availability_request_job():
    """
    Runs Mon/Tue/Wed 09:00 IL.
    For each active employee with a phone, kicks off the day-by-day availability flow
    for next week — but only if they haven't already submitted for that week,
    and aren't currently in the middle of answering.
    """
    from datetime import date
    from app.models.employee import Employee
    from app.models.availability import AvailabilitySubmission
    from app.models.schedule_week import ScheduleWeek
    from app.models.whatsapp_session import WhatsAppSession
    from app.api.v1.whatsapp import (
        next_week_sunday,
        get_org_operating_days,
        get_day_slot_saturation,
        send_interactive_day_question,
        send_whatsapp_to,
        day_question_message,
    )

    week_start = next_week_sunday()
    week_end = week_start + timedelta(days=6)
    print(f"[avail_req] starting — target week {week_start} → {week_end}", flush=True)

    async with async_session_factory() as db:
        # Active employees with phones, grouped by org
        emps_result = await db.execute(
            select(Employee).where(
                Employee.is_active == True,
                Employee.phone.isnot(None),
                Employee.phone != "",
            )
        )
        employees = emps_result.scalars().all()
        if not employees:
            print("[avail_req] no active employees with phones", flush=True)
            return

        by_org: dict[str, list[Employee]] = {}
        for emp in employees:
            by_org.setdefault(emp.org_id, []).append(emp)

        total_sent = 0
        total_skipped = 0

        for org_id, org_emps in by_org.items():
            operating_days = await get_org_operating_days(org_id, db)
            if not operating_days:
                print(f"[avail_req] org {org_id} has no operating days configured — skipping", flush=True)
                continue

            # Find existing ScheduleWeek for next week (may not exist yet)
            week_result = await db.execute(
                select(ScheduleWeek).where(
                    ScheduleWeek.org_id == org_id,
                    ScheduleWeek.week_start == week_start,
                )
            )
            week = week_result.scalar_one_or_none()

            # Collect employee_ids who already submitted for this week
            submitted_ids: set[str] = set()
            if week:
                sub_result = await db.execute(
                    select(AvailabilitySubmission.employee_id).where(
                        AvailabilitySubmission.week_id == week.id,
                    )
                )
                submitted_ids = {row[0] for row in sub_result.all()}

            first_day_idx = operating_days[0]
            first_date = week_start + timedelta(days=first_day_idx)

            for emp in org_emps:
                if emp.id in submitted_ids:
                    total_skipped += 1
                    continue

                # Skip if employee is mid-flow for this same week
                sess_result = await db.execute(
                    select(WhatsAppSession).where(WhatsAppSession.phone == emp.phone)
                )
                sess = sess_result.scalar_one_or_none()
                if sess and sess.state in ("availability_day_by_day", "availability_confirm"):
                    ctx = sess.context or {}
                    if ctx.get("week_start") == week_start.isoformat():
                        total_skipped += 1
                        continue

                # Initialize session
                if sess is None:
                    sess = WhatsAppSession(phone=emp.phone)
                    db.add(sess)
                sess.state = "availability_day_by_day"
                sess.context = {
                    "week_start": week_start.isoformat(),
                    "operating_days": operating_days,
                    "responses": {},
                    "step": 0,
                }
                sess.updated_at = datetime.now(timezone.utc)

                saturation = await get_day_slot_saturation(week_start, org_id, emp.id, db)
                first_sat = saturation.get(first_day_idx, {})
                sent = await send_interactive_day_question(
                    emp.phone, first_day_idx, first_date,
                    week_start, week_end, 1, len(operating_days), first_sat,
                )
                if not sent:
                    # Fallback to plain text — still kicks off the flow
                    await send_whatsapp_to(
                        emp.phone,
                        day_question_message(
                            first_day_idx, first_date, week_start, week_end,
                            1, len(operating_days), first_sat,
                        ),
                    )

                total_sent += 1
                print(f"[avail_req] sent to {emp.name} ({emp.phone})", flush=True)

        await db.commit()
        print(f"[avail_req] done — sent={total_sent} skipped={total_skipped}", flush=True)
