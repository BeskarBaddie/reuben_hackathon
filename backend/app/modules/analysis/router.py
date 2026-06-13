from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import AnalysisQueued, AnalysisRead
from app.modules.analysis.service import AnalysisService, run_analysis_job
from app.modules.auth.dependencies import get_current_user_id

router = APIRouter(tags=["analysis"])


def get_analysis_service(session: Session = Depends(get_session)) -> AnalysisService:
    return AnalysisService(AnalysisRepository(session))


@router.post(
    "/farms/{farm_id}/analyses",
    response_model=AnalysisQueued,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(
    farm_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisQueued:
    analysis = service.start_analysis(farm_id=farm_id, owner_id=user_id)
    background_tasks.add_task(run_analysis_job, analysis.id)
    return AnalysisQueued(analysis_id=analysis.id, status=analysis.status)


@router.get("/analyses/{analysis_id}", response_model=AnalysisRead)
def get_analysis(
    analysis_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisRead:
    return service.get_analysis(analysis_id=analysis_id, owner_id=user_id)
