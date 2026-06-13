from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.recommendations.repository import RecommendationRepository
from app.modules.recommendations.schemas import RecommendationRead
from app.modules.recommendations.service import RecommendationService

router = APIRouter(tags=["recommendations"])


def get_recommendation_service(session: Session = Depends(get_session)) -> RecommendationService:
    return RecommendationService(RecommendationRepository(session))


@router.post(
    "/analyses/{analysis_id}/recommendations",
    response_model=RecommendationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recommendations(
    analysis_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRead:
    return service.generate(analysis_id=analysis_id, owner_id=user_id)


@router.get("/recommendations/latest", response_model=RecommendationRead)
def get_latest_recommendation(
    user_id: UUID = Depends(get_current_user_id),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRead:
    return service.get_latest_for_owner(owner_id=user_id)


@router.get("/analyses/{analysis_id}/recommendations", response_model=RecommendationRead)
def get_recommendations(
    analysis_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRead:
    return service.get_latest(analysis_id=analysis_id, owner_id=user_id)
