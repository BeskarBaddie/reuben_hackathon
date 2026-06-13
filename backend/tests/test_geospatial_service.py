import pytest

from app.modules.geospatial.schemas import PolygonGeometry
from app.modules.geospatial.service import InvalidBoundaryError, geospatial_service


def test_area_hectares_for_valid_polygon() -> None:
    boundary = PolygonGeometry(
        type="Polygon",
        coordinates=[
            [
                (0.0, 0.0),
                (0.001, 0.0),
                (0.001, 0.001),
                (0.0, 0.001),
                (0.0, 0.0),
            ]
        ],
    )

    assert geospatial_service.area_hectares(boundary) > 1


def test_rejects_invalid_polygon() -> None:
    boundary = PolygonGeometry(
        type="Polygon",
        coordinates=[
            [
                (0.0, 0.0),
                (1.0, 1.0),
                (1.0, 0.0),
                (0.0, 1.0),
                (0.0, 0.0),
            ]
        ],
    )

    with pytest.raises(InvalidBoundaryError):
        geospatial_service.parse_polygon(boundary)
