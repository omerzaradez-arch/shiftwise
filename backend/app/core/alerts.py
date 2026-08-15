"""
Background alert jobs — runs on a schedule via APScheduler.

All sending goes through app.core.wa, so the active provider (Meta Cloud API or
Twilio) is decided by the WHATSAPP_PROVIDER env var, not by this module.

Jobs:
  - shift_start_notify: every 5 min — sends start-of-shift WhatsApp with quick-reply buttons
  - checkin_alert: every 5 min — late reminder for employees who missed check-in
  - availability_request: Mon/Tue/Wed 09:00 IL — kicks off weekly availability flow for employees who haven't submitted
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_

from app.database import async_session_factory


async def shift_start_notify_job():
    """
    Every 5 minutes:
    Find shifts that started in the last 5 minutes and haven't been notified yet.
    Send a WhatsApp quick-reply with "התחלתי" / "עוד לא התחלתי".
    """
    from app.models.scheduled_shift import ScheduledShift
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from app.core import wa

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

            start_str = shift.start_time.strftime("%H:%M")
            ok = await wa.notify_shift_start(emp.phone, emp.name, start_str)

            shift.checkin_notified = True
            print(f"[start_notify] sent to {emp.name} ({emp.phone}) shift={start_str} ok={ok}", flush=True)

        await db.commit()


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
    from app.core import wa

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
            ok = await wa.notify_shift_late(emp.phone, emp.name, start_str)
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
    from app.models.employee import Employee
    from app.models.availability import AvailabilitySubmission
    from app.models.schedule_week import ScheduleWeek
    from app.models.whatsapp_session import WhatsAppSession
    from app.core import wa
    from app.api.v1.whatsapp_meta import (
        DAY_NAMES,
        next_week_sunday,
        get_org_operating_days,
        send_day_availability_buttons,
    )

    week_start = next_week_sunday()
    week_end = week_start + timedelta(days=6)
    print(f"[avail_req] starting - target week {week_start} .. {week_end}", flush=True)

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

                # Preferred path: an approved template. Meta only permits
                # free-form messages inside the 24h customer-service window, and
                # a Monday-morning kickoff is almost always outside it. The
                # employee taps the template's button and the webhook opens the
                # day-by-day flow itself — so don't touch the session here.
                if await wa.request_availability(emp.phone, emp.name, week_start, week_end):
                    total_sent += 1
                    print(f"[avail_req] template sent to {emp.name} ({emp.phone})", flush=True)
                    continue

                # Fallback (inside the window / local testing): seed the session
                # and push the first day question straight away.
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

                await send_day_availability_buttons(
                    emp.phone, DAY_NAMES[first_day_idx], first_date,
                    week_start, week_end, 1, len(operating_days),
                )

                total_sent += 1
                print(f"[avail_req] interactive sent to {emp.name} ({emp.phone})", flush=True)

        await db.commit()
        print(f"[avail_req] done — sent={total_sent} skipped={total_skipped}", flush=True)
