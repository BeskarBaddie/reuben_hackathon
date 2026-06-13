"""Short-term weather forecast for the recommendation engine.

The forecast is forward-looking evidence (the climate module summarises the
*past* season; this module looks *ahead*). It mirrors the climate provider
pattern: a deterministic local ``MockForecastProvider`` is the default so the
system runs fully offline, with an optional Open-Meteo provider (free, no API
key) available behind the ``FORECAST_PROVIDER`` setting.

Like every other signal, the forecast is only evidence — the LLM never computes
it; it is produced here and stored in the evidence snapshot.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import settings
from app.modules.farms.models import Farm


class ForecastProvider(Protocol):
    def summarize(self, farm: Farm, climate: dict) -> dict:
        ...


def _classify_forecast_signal(
    rainfall_outlook_percent: float | None,
    temperature_anomaly_c: float | None,
) -> str:
    if rainfall_outlook_percent is None and temperature_anomaly_c is None:
        return "insufficient data"
    wet = rainfall_outlook_percent is not None and rainfall_outlook_percent >= 40
    dry = rainfall_outlook_percent is not None and rainfall_outlook_percent <= -25
    hot = temperature_anomaly_c is not None and temperature_anomaly_c >= 1.5
    if wet:
        return "wetter than normal"
    if dry and hot:
        return "hot and dry"
    if dry:
        return "drier than normal"
    if hot:
        return "hotter than normal"
    return "near normal"


class MockForecastProvider:
    """Deterministic local forecast that continues the recent seasonal trend.

    The outlook regresses part-way back toward normal (a short-term forecast is
    less extreme than a whole-season anomaly) and adds a small crop-derived
    jitter so different farms differ without using a random source.
    """

    source = "mock-deterministic-forecast"

    def summarize(self, farm: Farm, climate: dict) -> dict:
        horizon = settings.forecast_horizon_days
        season_days = max(settings.climate_season_days, 1)
        jitter = (sum(ord(char) for char in farm.crop.lower()) % 11) - 5  # -5..+5

        season_average = climate.get("rainfall_historical_average_mm")
        rainfall_normal = (
            round(season_average * horizon / season_days, 1)
            if isinstance(season_average, (int, float))
            else round(3.0 * horizon, 1)
        )
        season_rain_anomaly = climate.get("rainfall_anomaly_percent")
        rainfall_outlook_percent = (
            round(season_rain_anomaly * 0.5 + jitter, 1)
            if isinstance(season_rain_anomaly, (int, float))
            else float(jitter)
        )
        rainfall_outlook = round(
            max(rainfall_normal * (1 + rainfall_outlook_percent / 100), 0.0), 1
        )

        temperature_normal = climate.get("temperature_historical_average_c")
        if not isinstance(temperature_normal, (int, float)):
            temperature_normal = 25.0
        season_temp_anomaly = climate.get("temperature_anomaly_c")
        temperature_anomaly = (
            round(season_temp_anomaly * 0.6 + jitter * 0.05, 1)
            if isinstance(season_temp_anomaly, (int, float))
            else 0.0
        )
        temperature_outlook = round(temperature_normal + temperature_anomaly, 1)

        return {
            "horizon_days": horizon,
            "rainfall_outlook_mm": rainfall_outlook,
            "rainfall_normal_mm": rainfall_normal,
            "rainfall_outlook_percent": rainfall_outlook_percent,
            "temperature_outlook_c": temperature_outlook,
            "temperature_normal_c": round(float(temperature_normal), 1),
            "temperature_anomaly_c": temperature_anomaly,
            "forecast_signal": _classify_forecast_signal(
                rainfall_outlook_percent, temperature_anomaly
            ),
            "confidence": "low",
            "source": self.source,
            "evidence": {
                "provider": self.source,
                "method": (
                    "Deterministic local outlook extrapolated from the recent "
                    "seasonal anomaly, regressed toward normal."
                ),
                "horizon_days": horizon,
            },
        }


class OpenMeteoForecastProvider:
    """Optional free forecast from Open-Meteo (no API key required)."""

    source = "open-meteo"
    endpoint = "https://api.open-meteo.com/v1/forecast"

    def summarize(self, farm: Farm, climate: dict) -> dict:
        import httpx

        latitude, longitude = _farm_centroid(farm)
        horizon = settings.forecast_horizon_days
        response = httpx.get(
            self.endpoint,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
                "forecast_days": min(max(horizon, 1), 16),
                "timezone": "auto",
            },
            timeout=30,
        )
        response.raise_for_status()
        daily = response.json().get("daily", {})
        precipitation = [value for value in daily.get("precipitation_sum", []) if value is not None]
        highs = [value for value in daily.get("temperature_2m_max", []) if value is not None]
        lows = [value for value in daily.get("temperature_2m_min", []) if value is not None]

        rainfall_outlook = round(sum(precipitation), 1) if precipitation else None
        temperatures = [(high + low) / 2 for high, low in zip(highs, lows)]
        temperature_outlook = round(sum(temperatures) / len(temperatures), 1) if temperatures else None

        rainfall_normal = climate.get("rainfall_historical_average_mm")
        rainfall_normal = (
            round(rainfall_normal * horizon / max(settings.climate_season_days, 1), 1)
            if isinstance(rainfall_normal, (int, float))
            else None
        )
        rainfall_outlook_percent = (
            round(((rainfall_outlook - rainfall_normal) / rainfall_normal) * 100, 1)
            if rainfall_outlook is not None and rainfall_normal not in (None, 0)
            else None
        )
        temperature_normal = climate.get("temperature_historical_average_c")
        temperature_anomaly = (
            round(temperature_outlook - temperature_normal, 1)
            if temperature_outlook is not None and isinstance(temperature_normal, (int, float))
            else None
        )

        return {
            "horizon_days": horizon,
            "rainfall_outlook_mm": rainfall_outlook,
            "rainfall_normal_mm": rainfall_normal,
            "rainfall_outlook_percent": rainfall_outlook_percent,
            "temperature_outlook_c": temperature_outlook,
            "temperature_normal_c": (
                round(float(temperature_normal), 1)
                if isinstance(temperature_normal, (int, float))
                else None
            ),
            "temperature_anomaly_c": temperature_anomaly,
            "forecast_signal": _classify_forecast_signal(
                rainfall_outlook_percent, temperature_anomaly
            ),
            "confidence": "medium",
            "source": self.source,
            "evidence": {
                "provider": self.source,
                "latitude": round(latitude, 4),
                "longitude": round(longitude, 4),
                "horizon_days": horizon,
            },
        }


def _farm_centroid(farm: Farm) -> tuple[float, float]:
    """Return (latitude, longitude) of the farm boundary centroid."""
    boundary = farm.boundary
    if isinstance(boundary, str):
        from shapely import wkt

        geometry = wkt.loads(boundary)
    else:  # PostGIS WKBElement
        from geoalchemy2.shape import to_shape

        geometry = to_shape(boundary)
    centroid = geometry.centroid
    return float(centroid.y), float(centroid.x)


def get_forecast_provider() -> ForecastProvider:
    if settings.forecast_provider == "open_meteo":
        return OpenMeteoForecastProvider()
    return MockForecastProvider()


def build_forecast(farm: Farm, climate: dict) -> dict:
    """Produce a forecast block, falling back to the local mock on any error."""
    provider = get_forecast_provider()
    try:
        return provider.summarize(farm, climate)
    except Exception:
        if isinstance(provider, MockForecastProvider):
            raise
        forecast = MockForecastProvider().summarize(farm, climate)
        forecast["evidence"]["fallback_from"] = provider.source
        return forecast
