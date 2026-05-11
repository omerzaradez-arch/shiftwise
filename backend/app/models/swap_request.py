import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SwapRequest(Base):
    __tablename__ = "swap_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shift_id: Mapped[str] = mapped_column(String, ForeignKey("scheduled_shifts.id"), nullable=False)
    requester_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), nullable=False)
    target_employee_id: Mapped[str | None] = mapped_column(String, ForeignKey("employees.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending | approved | rejected | auto_approved
    reviewed_by: Mapped[str | None] = mapped_column(String, ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    shift: Mapped["ScheduledShift"] = relationship(back_populates="swap_request")
    requester: Mapped["Employee"] = relationship(foreign_keys=[requester_id])
    target_employee: Mapped["Employee | None"] = relationship(foreign_keys=[target_employee_id])
