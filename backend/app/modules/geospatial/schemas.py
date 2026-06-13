from typing import Any, Literal

from pydantic import BaseModel, Field


Position = tuple[float, float]
LinearRing = list[Position]


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[LinearRing] = Field(min_length=1)


class Feature(BaseModel):
    type: Literal["Feature"]
    geometry: PolygonGeometry
    properties: dict[str, Any] = Field(default_factory=dict)
