import uuid
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base


class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    phone: Mapped[str] = mapped_column(String(30), primary_key=True)
    state: Mapped[str] = mapped_column(String(50), default="idle")
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
