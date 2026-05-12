import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import String, Date, Time, Integer, Boolean, Text, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AvailabilitySubmission(Base):
    __tablename__ = "availability_submissions"
    __table_args__ = (UniqueConstraint("employee_id", "week_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), nullable=False)
    week_id: Mapped[str] = mapped_column(String, ForeignKey("schedule_weeks.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    desired_shifts_count: Mapped[int | None] = mapped_column(Integer)
    preferred_shift_types: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    # {day_index: {available, preferred_types, is_hard}}
    # e.g. {"0": {"available": true, "preferred_types": ["evening"], "is_hard": false}}
    day_preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    employee: Mapped["Employee"] = relationship(back_populates="availability_submissions")
    unavailability_slots: Mapped[list["UnavailabilitySlot"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class UnavailabilitySlot(Base):
    __tablename__ = "unavailability_slots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[str] = mapped_column(
        String, ForeignKey("availability_submissions.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(255))
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean, default=True)

    submission: Mapped["AvailabilitySubmission"] = relationship(
        back_populates="unavailability_slots"
    )
