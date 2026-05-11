import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(50), default="junior")
    employment_type: Mapped[str] = mapped_column(String(50), default="part_time")

    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=40)
    min_hours_per_week: Mapped[int] = mapped_column(Integer, default=0)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, default=5)
    skills: Mapped[list] = mapped_column(JSON, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(back_populates="employees")
    availability_submissions: Mapped[list["AvailabilitySubmission"]] = relationship(
        back_populates="employee"
    )
    scheduled_shifts: Mapped[list["ScheduledShift"]] = relationship(
        back_populates="employee"
    )
