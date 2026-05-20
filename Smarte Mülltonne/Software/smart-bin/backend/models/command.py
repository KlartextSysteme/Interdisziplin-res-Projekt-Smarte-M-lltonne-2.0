from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bin_id: Mapped[int] = mapped_column(Integer, ForeignKey("bins.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)   # lock | unlock | empty | ...
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ack_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
