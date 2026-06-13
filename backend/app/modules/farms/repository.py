from uuid import UUID

from geoalchemy2.shape import from_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.farms.models import Farm
from app.modules.farms.schemas import FarmCreate
from app.modules.geospatial.service import geospatial_service


class FarmRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, owner_id: UUID, payload: FarmCreate) -> Farm:
        polygon = geospatial_service.parse_polygon(payload.boundary)
        farm = Farm(
            owner_id=owner_id,
            name=payload.name,
            crop=payload.crop,
            planting_date=payload.planting_date,
            expected_harvest_date=payload.expected_harvest_date,
            irrigation_type=payload.irrigation_type,
            area_hectares=geospatial_service.area_hectares(payload.boundary),
            boundary=polygon.wkt
            if settings.database_url.startswith("sqlite")
            else from_shape(polygon, srid=4326),
            notes=payload.notes,
        )
        self.session.add(farm)
        self.session.commit()
        self.session.refresh(farm)
        return farm

    def list_for_owner(self, owner_id: UUID) -> list[Farm]:
        statement = select(Farm).where(Farm.owner_id == owner_id).order_by(Farm.created_at.desc())
        return list(self.session.scalars(statement).all())

    def get_for_owner(self, farm_id: UUID, owner_id: UUID) -> Farm | None:
        statement = select(Farm).where(Farm.id == farm_id, Farm.owner_id == owner_id)
        return self.session.scalar(statement)

    def delete_for_owner(self, farm_id: UUID, owner_id: UUID) -> bool:
        farm = self.get_for_owner(farm_id=farm_id, owner_id=owner_id)
        if not farm:
            return False
        self.session.delete(farm)
        self.session.commit()
        return True
