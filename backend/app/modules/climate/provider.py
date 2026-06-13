from datetime import UTC, date, datetime, timedelta
from statistics import mean
from typing import Protocol

from shapely import wkt
from shapely.geometry import mapping

from app.core.config import settings
from app.modules.climate.schemas import ClimateSummary
from app.modules.farms.models import Farm


class ClimateProvider(Protocol):
    def summarize(self, farm: Farm, boundary_wkt: str) -> ClimateSummary:
        pass


class MockClimateProvider:
    source = "mock-deterministic-climate"

    def summarize(self, farm: Farm, boundary_wkt: str) -> ClimateSummary:
        season_end = datetime.now(UTC).date()
        season_start = season_end - timedelta(days=settings.climate_season_days)
        crop_factor = sum(ord(char) for char in farm.crop.lower()) % 35
        rainfall_this = round(210 + crop_factor + min(farm.area_hectares, 50) * 0.8, 1)
        rainfall_average = 300.0
        rainfall_anomaly = round(((rainfall_this - rainfall_average) / rainfall_average) * 100, 1)
        temperature_this = round(25.5 + (crop_factor / 30), 1)
        temperature_average = 24.7
        temperature_anomaly = round(temperature_this - temperature_average, 1)

        return ClimateSummary(
            season_start=season_start.isoformat(),
            season_end=season_end.isoformat(),
            rainfall_this_season_mm=rainfall_this,
            rainfall_historical_average_mm=rainfall_average,
            rainfall_anomaly_percent=rainfall_anomaly,
            temperature_this_season_c=temperature_this,
            temperature_historical_average_c=temperature_average,
            temperature_anomaly_c=temperature_anomaly,
            climate_signal=_classify_climate_signal(rainfall_anomaly, temperature_anomaly),
            source=self.source,
            evidence={
                "provider": self.source,
                "method": "Deterministic local placeholder until Earth Engine climate analysis is configured.",
                "season_days": settings.climate_season_days,
            },
        )


class EarthEngineClimateProvider:
    chirps_source = "UCSB-CHG/CHIRPS/DAILY"
    era5_source = "ECMWF/ERA5_LAND/DAILY_AGGR"

    def summarize(self, farm: Farm, boundary_wkt: str) -> ClimateSummary:
        if not settings.earth_engine_project_id:
            raise RuntimeError("EARTH_ENGINE_PROJECT_ID is required for climate analysis")

        import ee

        if settings.earth_engine_service_account_email and settings.earth_engine_service_account_key_path:
            credentials = ee.ServiceAccountCredentials(
                settings.earth_engine_service_account_email,
                settings.earth_engine_service_account_key_path,
            )
            ee.Initialize(credentials, project=settings.earth_engine_project_id)
        else:
            ee.Initialize(project=settings.earth_engine_project_id)

        polygon = wkt.loads(boundary_wkt)
        region = ee.Geometry(mapping(polygon))
        climate_region = region.buffer(12_000)
        season_end = datetime.now(UTC).date()
        season_start = season_end - timedelta(days=settings.climate_season_days)

        rainfall_this = _round_or_none(
            _chirps_rainfall_total(
                ee=ee,
                region=climate_region,
                start=season_start,
                end=season_end,
                source=self.chirps_source,
            ),
            1,
        )
        rainfall_baseline_values = [
            _chirps_rainfall_total(
                ee=ee,
                region=climate_region,
                start=_date_for_year(season_start, year),
                end=_date_for_year(season_end, year),
                source=self.chirps_source,
            )
            for year in range(
                settings.climate_baseline_start_year,
                settings.climate_baseline_end_year + 1,
            )
        ]
        rainfall_average = _round_or_none(_mean_without_none(rainfall_baseline_values), 1)
        rainfall_anomaly = (
            round(((rainfall_this - rainfall_average) / rainfall_average) * 100, 1)
            if rainfall_this is not None and rainfall_average not in (None, 0)
            else None
        )

        temperature_this = _round_or_none(
            _era5_temperature_mean(
                ee=ee,
                region=climate_region,
                start=season_start,
                end=season_end,
                source=self.era5_source,
            ),
            1,
        )
        temperature_baseline_values = [
            _era5_temperature_mean(
                ee=ee,
                region=climate_region,
                start=_date_for_year(season_start, year),
                end=_date_for_year(season_end, year),
                source=self.era5_source,
            )
            for year in range(
                settings.climate_baseline_start_year,
                settings.climate_baseline_end_year + 1,
            )
        ]
        temperature_average = _round_or_none(_mean_without_none(temperature_baseline_values), 1)
        temperature_anomaly = (
            round(temperature_this - temperature_average, 1)
            if temperature_this is not None and temperature_average is not None
            else None
        )

        return ClimateSummary(
            season_start=season_start.isoformat(),
            season_end=season_end.isoformat(),
            rainfall_this_season_mm=rainfall_this,
            rainfall_historical_average_mm=rainfall_average,
            rainfall_anomaly_percent=rainfall_anomaly,
            temperature_this_season_c=temperature_this,
            temperature_historical_average_c=temperature_average,
            temperature_anomaly_c=temperature_anomaly,
            climate_signal=_classify_climate_signal(rainfall_anomaly, temperature_anomaly),
            source=f"{self.chirps_source}; {self.era5_source}",
            evidence={
                "provider": "earth_engine",
                "rainfall_dataset": self.chirps_source,
                "temperature_dataset": self.era5_source,
                "rainfall_band": "precipitation",
                "temperature_band": "temperature_2m",
                "season_days": settings.climate_season_days,
                "season_start": season_start.isoformat(),
                "season_end": season_end.isoformat(),
                "baseline_start_year": settings.climate_baseline_start_year,
                "baseline_end_year": settings.climate_baseline_end_year,
                "rainfall_scale_meters": 5566,
                "temperature_scale_meters": 11132,
                "climate_sampling_buffer_meters": 12000,
            },
        )


def get_climate_provider() -> ClimateProvider:
    if settings.climate_provider == "mock" or settings.remote_sensing_provider == "mock":
        return MockClimateProvider()
    return EarthEngineClimateProvider()


def _chirps_rainfall_total(ee, region, start: date, end: date, source: str) -> float | None:
    image = (
        ee.ImageCollection(source)
        .filterDate(start.isoformat(), end.isoformat())
        .select("precipitation")
        .sum()
    )
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=5566,
        maxPixels=1_000_000_000,
    ).getInfo()
    value = stats.get("precipitation")
    return float(value) if value is not None else None


def _era5_temperature_mean(ee, region, start: date, end: date, source: str) -> float | None:
    image = (
        ee.ImageCollection(source)
        .filterDate(start.isoformat(), end.isoformat())
        .select("temperature_2m")
        .mean()
    )
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=11132,
        maxPixels=1_000_000_000,
    ).getInfo()
    value = stats.get("temperature_2m")
    return float(value) - 273.15 if value is not None else None


def _date_for_year(source_date: date, year: int) -> date:
    try:
        return source_date.replace(year=year)
    except ValueError:
        return source_date.replace(year=year, day=28)


def _mean_without_none(values: list[float | None]) -> float | None:
    usable_values = [value for value in values if value is not None]
    return mean(usable_values) if usable_values else None


def _round_or_none(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def _classify_climate_signal(
    rainfall_anomaly_percent: float | None,
    temperature_anomaly_c: float | None,
) -> str:
    if rainfall_anomaly_percent is None and temperature_anomaly_c is None:
        return "insufficient data"
    dry = rainfall_anomaly_percent is not None and rainfall_anomaly_percent <= -25
    wet = rainfall_anomaly_percent is not None and rainfall_anomaly_percent >= 25
    hot = temperature_anomaly_c is not None and temperature_anomaly_c >= 1.5
    if dry and hot:
        return "hot and dry"
    if dry:
        return "drier than usual"
    if wet:
        return "wetter than usual"
    if hot:
        return "hotter than usual"
    return "near historical average"
