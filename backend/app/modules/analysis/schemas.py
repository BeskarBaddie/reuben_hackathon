from enum import StrEnum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisQueued(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus = AnalysisStatus.PROCESSING


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    farm_id: UUID
    status: AnalysisStatus
    ndvi: float | None
    vegetation_health: str | None
    vegetation_trend: str | None
    water_stress: str | None
    image_date: str | None
    source: str | None
    evidence: dict[str, Any] | None
    climate_season_start: str | None
    climate_season_end: str | None
    rainfall_this_season_mm: float | None
    rainfall_historical_average_mm: float | None
    rainfall_anomaly_percent: float | None
    temperature_this_season_c: float | None
    temperature_historical_average_c: float | None
    temperature_anomaly_c: float | None
    climate_signal: str | None
    climate_source: str | None
    climate_evidence: dict[str, Any] | None
    drought_score: int | None
    drought_level: str | None
    drought_drivers: list[str] | None
    flood_score: int | None
    flood_level: str | None
    flood_drivers: list[str] | None
    heat_score: int | None
    heat_level: str | None
    heat_drivers: list[str] | None
    overall_risk_level: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
