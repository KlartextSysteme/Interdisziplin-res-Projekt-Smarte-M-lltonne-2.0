from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bin_id: Mapped[int] = mapped_column(Integer, ForeignKey("bins.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)      # tamper|theft_attempt|unauthorized_open
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
