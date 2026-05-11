import uuid
from datetime import date, time
from sqlalchemy import String, Date, Time, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ScheduledShift(Base):
    __tablename__ = "scheduled_shifts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    week_id: Mapped[str] = mapped_column(String, ForeignKey("schedule_weeks.id"), nullable=False)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("shift_templates.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="assigned")
    # assigned | swap_requested | swap_approved | cancelled
    is_manually_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(50), default="optimizer")
    # optimizer | manager

    week: Mapped["ScheduleWeek"] = relationship(back_populates="scheduled_shifts")
    template: Mapped["ShiftTemplate"] = relationship()
    employee: Mapped["Employee"] = relationship(back_populates="scheduled_shifts")
    swap_request: Mapped["SwapRequest | None"] = relationship(back_populates="shift", uselist=False)
