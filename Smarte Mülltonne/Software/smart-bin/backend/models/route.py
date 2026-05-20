from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    waypoints: Mapped[list] = mapped_column(JSON, default=list)          # ordered bin IDs
    distance_m: Mapped[int] = mapped_column(Integer, default=0)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Planar reference distances for the NN-vs-2opt comparison badge.
    # distance_m is OSRM-based (real streets, after 2-opt); these two are
    # planar (haversine), used purely for the optimization-percent display.
    nn_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    optimized_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Held-Karp exakte Lösung — nur für kleine Instanzen (n ≤ 15) berechnet,
    # weil O(n²·2ⁿ) sonst zu langsam wird. Dient als Optimum-Referenz für 2-opt.
    exact_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # GeoJSON LineString
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
