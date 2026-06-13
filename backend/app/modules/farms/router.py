from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.farms.repository import FarmRepository
from app.modules.farms.schemas import FarmCreate, FarmCreated, FarmRead
from app.modules.farms.service import FarmService
from app.modules.geospatial.service import InvalidBoundaryError

router = APIRouter(prefix="/farms", tags=["farms"])


def get_farm_service(session: Session = Depends(get_session)) -> FarmService:
    return FarmService(FarmRepository(session))


@router.post("", response_model=FarmCreated, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: FarmService = Depends(get_farm_service),
) -> FarmCreated:
    try:
        farm = service.create_farm(owner_id=user_id, payload=payload)
    except InvalidBoundaryError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return FarmCreated(farm=farm)


@router.get("", response_model=list[FarmRead])
def list_farms(
    user_id: UUID = Depends(get_current_user_id),
    service: FarmService = Depends(get_farm_service),
) -> list[FarmRead]:
    return service.list_farms(owner_id=user_id)


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: FarmService = Depends(get_farm_service),
) -> Response:
    deleted = service.delete_farm(farm_id=farm_id, owner_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
