from uuid import UUID

from app.modules.farms.models import Farm
from app.modules.farms.repository import FarmRepository
from app.modules.farms.schemas import FarmCreate


class FarmService:
    def __init__(self, repository: FarmRepository):
        self.repository = repository

    def create_farm(self, owner_id: UUID, payload: FarmCreate) -> Farm:
        return self.repository.create(owner_id=owner_id, payload=payload)

    def list_farms(self, owner_id: UUID) -> list[Farm]:
        return self.repository.list_for_owner(owner_id=owner_id)
