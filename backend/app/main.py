import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
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

COLUMN_MIGRATIONS = [
    "ALTER TABLE availability_submissions ADD COLUMN IF NOT EXISTS day_preferences JSON DEFAULT '{}'",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS hourly_rate FLOAT",
    "ALTER TABLE scheduled_shifts ADD COLUMN IF NOT EXISTS checkin_notified BOOLEAN DEFAULT FALSE",
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
    from app.core.alerts import checkin_alert_job

    scheduler = AsyncIOScheduler(timezone="Asia/Jerusalem")
    scheduler.add_job(
        checkin_alert_job,
        trigger="interval",
        minutes=5,
        id="checkin_alert",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    print("[scheduler] started — checkin_alert every 5 min", flush=True)

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
app.include_router(whatsapp_router.router, prefix="/api/v1/whatsapp", tags=["whatsapp"])
app.include_router(whatsapp_meta_router.router, prefix="/api/v1/whatsapp_meta", tags=["whatsapp-meta"])
app.include_router(simulate_router.router, prefix="/api/v1/simulate", tags=["simulate"])
app.include_router(public_router.router, prefix="/api/v1/public", tags=["public"])
app.include_router(attendance_router.router, prefix="/api/v1/attendance", tags=["attendance"])
app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["notifications"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
