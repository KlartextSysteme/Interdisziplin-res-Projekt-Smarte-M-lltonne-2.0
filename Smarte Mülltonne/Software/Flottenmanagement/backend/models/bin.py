from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Bin(Base):
    __tablename__ = "bins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False, default="")
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_level: Mapped[int] = mapped_column(Integer, default=0)          # 0–100 %
    battery: Mapped[int] = mapped_column(Integer, default=100)           # 0–100 %
    solar_output_w: Mapped[float] = mapped_column(Float, default=0.0)
    is_charging: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="idle")          # idle|en_route|emptied|locked
    location_state: Mapped[str] = mapped_column(String, default="home")  # home|truck|docking|unknown
    movement_state: Mapped[str] = mapped_column(String, default="home")  # home|moving_to_pickup|pickup|moving_home
    movement_model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
