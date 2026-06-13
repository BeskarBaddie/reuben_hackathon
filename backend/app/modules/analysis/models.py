import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.analysis.schemas import AnalysisStatus


class FarmAnalysis(Base):
    __tablename__ = "farm_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            name="analysis_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=AnalysisStatus.PROCESSING,
        nullable=False,
    )
    ndvi: Mapped[float | None] = mapped_column(Float, nullable=True)
    vegetation_health: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vegetation_trend: Mapped[str | None] = mapped_column(String(80), nullable=True)
    water_stress: Mapped[str | None] = mapped_column(String(80), nullable=True)
    image_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    climate_season_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    climate_season_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rainfall_this_season_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_historical_average_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_anomaly_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_this_season_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_historical_average_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_anomaly_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    climate_signal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    climate_source: Mapped[str | None] = mapped_column(String(220), nullable=True)
    climate_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    drought_score: Mapped[int | None] = mapped_column(nullable=True)
    drought_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    drought_drivers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    flood_score: Mapped[int | None] = mapped_column(nullable=True)
    flood_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    flood_drivers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    heat_score: Mapped[int | None] = mapped_column(nullable=True)
    heat_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    heat_drivers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    overall_risk_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
