from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from app.modules.geospatial.schemas import Feature, PolygonGeometry


class InvalidBoundaryError(ValueError):
    pass


class GeospatialService:
    def parse_polygon(self, boundary: Feature | PolygonGeometry) -> BaseGeometry:
        geometry_payload = boundary.geometry.model_dump() if isinstance(boundary, Feature) else boundary.model_dump()
        geometry = shape(geometry_payload)

        if geometry.is_empty:
            raise InvalidBoundaryError("Boundary polygon is empty")
        if geometry.geom_type != "Polygon":
            raise InvalidBoundaryError("Boundary must be a single Polygon")
        if not geometry.is_valid:
            raise InvalidBoundaryError("Boundary polygon is invalid")

        return geometry

    def area_hectares(self, boundary: Feature | PolygonGeometry) -> float:
        polygon = self.parse_polygon(boundary)
        # Approximate equal-area calculation without forcing GeoPandas/pyproj into the API path.
        lon, lat = polygon.centroid.x, polygon.centroid.y
        meters_per_degree_lat = 111_132.92
        meters_per_degree_lon = 111_412.84
        projected = transform(
            lambda x, y, z=None: (
                (x - lon) * meters_per_degree_lon,
                (y - lat) * meters_per_degree_lat,
            ),
            polygon,
        )
        return round(projected.area / 10_000, 4)

    def to_wkt(self, boundary: Feature | PolygonGeometry) -> str:
        return self.parse_polygon(boundary).wkt


geospatial_service = GeospatialService()
