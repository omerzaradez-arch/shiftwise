import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Date, Float, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)

    date: Mapped[date] = mapped_column(Date, nullable=False)

    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    check_in_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_valid_location: Mapped[bool] = mapped_column(Boolean, default=True)

    total_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # filled on checkout

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    employee: Mapped["Employee"] = relationship("Employee")
