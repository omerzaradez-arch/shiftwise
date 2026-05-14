"""
Background alert jobs — runs on a schedule via APScheduler.
Currently:
  - checkin_alert: every 5 min — notifies employees who missed check-in
"""

from datetime import datetime, timedelta, timezone, time as dtime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


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

        await db.commit()
