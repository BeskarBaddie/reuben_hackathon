from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.farms.models import IrrigationType
from app.modules.geospatial.schemas import Feature, PolygonGeometry


BoundaryInput = Feature | PolygonGeometry


class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    crop: str = Field(min_length=1, max_length=120)
    boundary: BoundaryInput
    planting_date: date | None = None
    expected_harvest_date: date | None = None
    irrigation_type: IrrigationType = IrrigationType.RAINFED
    notes: str | None = Field(default=None, max_length=4_000)


class FarmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    crop: str
    planting_date: date | None
    expected_harvest_date: date | None
    irrigation_type: IrrigationType
    area_hectares: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


class FarmCreated(BaseModel):
    farm: FarmRead
    next_step: str = "analysis_not_started"
