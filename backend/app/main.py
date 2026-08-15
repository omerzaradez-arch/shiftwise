import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter

# ── Sentry: capture unhandled errors in production ─────────────────────────────
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production" if not settings.debug else "development"),
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")[:7],
        traces_sample_rate=0.1,  # 10% of requests traced for performance
        send_default_pii=False,  # don't send phone numbers etc to Sentry
        integrations=[FastApiIntegration(), StarletteIntegration()],
    )
    print(f"[sentry] enabled (env={os.getenv('SENTRY_ENVIRONMENT', 'production')})", flush=True)
else:
    print("[sentry] SENTRY_DSN not set — error monitoring disabled", flush=True)
from app.api.v1 import auth, employees, schedules, availability, shifts, swaps, analytics
from app.api.v1 import settings as settings_router
from app.api.v1 import shift_templates as shift_templates_router
from app.api.v1 import whatsapp as whatsapp_router
from app.api.v1 import whatsapp_meta as whatsapp_meta_router
from app.api.v1 import simulate as simulate_router
from app.api.v1 import public as public_router
from app.api.v1 import attendance as attendance_router
from app.api.v1 import notifications as notifications_router

logger = logging.getLogger(__name__)

_wa_provider = os.getenv("WHATSAPP_PROVIDER", "meta").strip().lower()
print(f"[whatsapp] provider={_wa_provider}", flush=True)

COLUMN_MIGRATIONS = [
    "ALTER TABLE availability_submissions ADD COLUMN IF NOT EXISTS day_preferences JSON DEFAULT '{}'",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS hourly_rate FLOAT",
    "ALTER TABLE scheduled_shifts ADD COLUMN IF NOT EXISTS checkin_notified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS tokens_invalidated_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP WITH TIME ZONE",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import async_engine, Base
    from sqlalchemy import text

    # ── DB migrations ──
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in COLUMN_MIGRATIONS:
            try:
                await conn.execute(text(sql))
                print(f"[migration] OK: {sql[:60]}", flush=True)
            except Exception as e:
                print(f"[migration] FAILED: {sql[:60]} — {e}", flush=True)

    # ── Background scheduler ──
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from app.core.alerts import checkin_alert_job, shift_start_notify_job, availability_request_job

    scheduler = AsyncIOScheduler(timezone="Asia/Jerusalem")
    scheduler.add_job(
        shift_start_notify_job,
        trigger="interval",
        minutes=5,
        id="shift_start_notify",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        checkin_alert_job,
        trigger="interval",
        minutes=5,
        id="checkin_alert",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        availability_request_job,
        trigger=CronTrigger(day_of_week="mon,tue,wed", hour=9, minute=0, timezone="Asia/Jerusalem"),
        id="availability_request",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    print("[scheduler] started — shift_start_notify+checkin_alert every 5min, availability_request Mon/Tue/Wed 09:00 IL", flush=True)

    yield

    scheduler.shutdown(wait=False)
    print("[scheduler] stopped", flush=True)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(employees.router, prefix="/api/v1/employees", tags=["employees"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])
app.include_router(availability.router, prefix="/api/v1/availability", tags=["availability"])
app.include_router(shifts.router, prefix="/api/v1/shifts", tags=["shifts"])
app.include_router(swaps.router, prefix="/api/v1/swaps", tags=["swaps"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(shift_templates_router.router, prefix="/api/v1/shift-templates", tags=["shift-templates"])
# Only the active provider's webhook is mounted, so an old Twilio webhook can't
# race the Meta one and answer the same employee twice.
if _wa_provider == "twilio":
    app.include_router(whatsapp_router.router, prefix="/api/v1/whatsapp", tags=["whatsapp"])
else:
    app.include_router(whatsapp_meta_router.router, prefix="/api/v1/whatsapp_meta", tags=["whatsapp-meta"])
app.include_router(simulate_router.router, prefix="/api/v1/simulate", tags=["simulate"])
app.include_router(public_router.router, prefix="/api/v1/public", tags=["public"])
app.include_router(attendance_router.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["notifications"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
