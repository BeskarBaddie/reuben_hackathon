from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from shapely import wkt
from shapely.geometry import mapping

from app.core.config import settings
from app.modules.farms.models import Farm


@dataclass(frozen=True)
class RemoteSensingResult:
    ndvi: float
    vegetation_health: str
    vegetation_trend: str
    water_stress: str
    image_date: str
    source: str
    evidence: dict


class RemoteSensingProvider(Protocol):
    def analyze(self, farm: Farm, boundary_wkt: str) -> RemoteSensingResult:
        pass


class MockRemoteSensingProvider:
    source = "mock-deterministic"

    def analyze(self, farm: Farm, boundary_wkt: str) -> RemoteSensingResult:
        crop_factor = (sum(ord(char) for char in farm.crop.lower()) % 18) / 100
        area_factor = min(farm.area_hectares, 10) / 100
        ndvi = round(max(0.18, min(0.82, 0.46 + crop_factor + area_factor)), 2)

        if ndvi >= 0.62:
            vegetation_health = "healthy"
            water_stress = "low"
        elif ndvi >= 0.42:
            vegetation_health = "moderate"
            water_stress = "medium"
        else:
            vegetation_health = "stressed"
            water_stress = "high"

        return RemoteSensingResult(
            ndvi=ndvi,
            vegetation_health=vegetation_health,
            vegetation_trend="insufficient data",
            water_stress=water_stress,
            image_date=datetime.now(UTC).date().isoformat(),
            source=self.source,
            evidence={
                "provider": self.source,
                "boundary_area_hectares": farm.area_hectares,
                "method": "Deterministic local placeholder until Earth Engine credentials are configured.",
            },
        )


class EarthEngineRemoteSensingProvider:
    source = "COPERNICUS/S2_SR_HARMONIZED"

    def analyze(self, farm: Farm, boundary_wkt: str) -> RemoteSensingResult:
        if not settings.earth_engine_project_id:
            raise RuntimeError("EARTH_ENGINE_PROJECT_ID is required for Earth Engine analysis")

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
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=settings.earth_engine_days_lookback)

        collection = (
            ee.ImageCollection(self.source)
            .filterBounds(region)
            .filterDate(start_date.isoformat(), end_date.isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        image = ee.Image(collection.first())
        ndvi_image = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
        stats = ndvi_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10,
            maxPixels=1_000_000_000,
        ).getInfo()

        if stats.get("ndvi") is None:
            raise RuntimeError("No usable Sentinel-2 NDVI pixels found for this farm and date window")

        ndvi = round(float(stats["ndvi"]), 3)
        image_date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()

        if ndvi >= 0.62:
            vegetation_health = "healthy"
            water_stress = "low"
        elif ndvi >= 0.42:
            vegetation_health = "moderate"
            water_stress = "medium"
        else:
            vegetation_health = "stressed"
            water_stress = "high"

        return RemoteSensingResult(
            ndvi=ndvi,
            vegetation_health=vegetation_health,
            vegetation_trend="insufficient data",
            water_stress=water_stress,
            image_date=image_date,
            source=self.source,
            evidence={
                "provider": "earth_engine",
                "dataset": self.source,
                "date_window_start": start_date.isoformat(),
                "date_window_end": end_date.isoformat(),
                "cloud_filter_percent": 30,
                "bands": ["B8", "B4"],
                "scale_meters": 10,
            },
        )


def get_remote_sensing_provider() -> RemoteSensingProvider:
    if settings.remote_sensing_provider == "earth_engine":
        return EarthEngineRemoteSensingProvider()
    return MockRemoteSensingProvider()
