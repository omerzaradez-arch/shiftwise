import uuid
from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FairnessTracking(Base):
    __tablename__ = "fairness_tracking"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[str] = mapped_column(String, ForeignKey("employees.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"), nullable=False)
    week_id: Mapped[str] = mapped_column(String, ForeignKey("schedule_weeks.id"), nullable=False)
    total_hours: Mapped[float] = mapped_column(Float, default=0)
    weekend_shifts: Mapped[int] = mapped_column(Integer, default=0)
    evening_shifts: Mapped[int] = mapped_column(Integer, default=0)
    morning_shifts: Mapped[int] = mapped_column(Integer, default=0)
    fairness_score: Mapped[float | None] = mapped_column(Float)
