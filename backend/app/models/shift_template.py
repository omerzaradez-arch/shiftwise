import uuid
from sqlalchemy import String, Time, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import time
from app.database import Base


class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shift_type: Mapped[str] = mapped_column(String(50), default="afternoon")
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    min_employees: Mapped[int] = mapped_column(Integer, default=1)
    max_employees: Mapped[int] = mapped_column(Integer, default=10)
    required_roles: Mapped[dict] = mapped_column(JSON, default=dict)
    days_of_week: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship(back_populates="shift_templates")

    @property
    def duration_hours(self) -> float:
        start = self.start_time.hour + self.start_time.minute / 60
        end = self.end_time.hour + self.end_time.minute / 60
        if end < start:
            end += 24
        return end - start
