import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Date, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ScheduleWeek(Base):
    __tablename__ = "schedule_weeks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="collecting")
    # collecting | generated | review | changes_requested | final | published
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    optimizer_score: Mapped[float | None] = mapped_column(Float)
    coverage_percent: Mapped[float | None] = mapped_column(Float)
    optimizer_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    organization: Mapped["Organization"] = relationship(back_populates="schedule_weeks")
    scheduled_shifts: Mapped[list["ScheduledShift"]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
