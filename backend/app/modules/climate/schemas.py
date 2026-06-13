from dataclasses import dataclass


@dataclass(frozen=True)
class ClimateSummary:
    season_start: str
    season_end: str
    rainfall_this_season_mm: float | None
    rainfall_historical_average_mm: float | None
    rainfall_anomaly_percent: float | None
    temperature_this_season_c: float | None
    temperature_historical_average_c: float | None
    temperature_anomaly_c: float | None
    climate_signal: str
    source: str
    evidence: dict
