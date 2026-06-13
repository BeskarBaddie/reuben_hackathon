from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.analysis.models import FarmAnalysis
from app.modules.farms.models import Farm
from app.modules.recommendations.models import Recommendation


class RecommendationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_analysis_for_owner(self, analysis_id: UUID, owner_id: UUID) -> FarmAnalysis | None:
        statement = (
            select(FarmAnalysis)
            .join(Farm, Farm.id == FarmAnalysis.farm_id)
            .where(FarmAnalysis.id == analysis_id, Farm.owner_id == owner_id)
        )
        return self.session.scalars(statement).first()

    def get_farm(self, farm_id: UUID) -> Farm | None:
        return self.session.get(Farm, farm_id)

    def latest_for_analysis(self, analysis_id: UUID) -> Recommendation | None:
        statement = (
            select(Recommendation)
            .where(Recommendation.analysis_id == analysis_id)
            .order_by(Recommendation.created_at.desc())
        )
        return self.session.scalars(statement).first()

    def latest_for_owner(self, owner_id: UUID) -> Recommendation | None:
        statement = (
            select(Recommendation)
            .join(FarmAnalysis, FarmAnalysis.id == Recommendation.analysis_id)
            .join(Farm, Farm.id == FarmAnalysis.farm_id)
            .where(Farm.owner_id == owner_id)
            .order_by(Recommendation.created_at.desc())
        )
        return self.session.scalars(statement).first()

    def create(
        self,
        analysis_id: UUID,
        provider: str,
        model: str | None,
        prompt_version: str,
        evidence_snapshot: dict,
        output: dict,
    ) -> Recommendation:
        recommendation = Recommendation(
            analysis_id=analysis_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            evidence_snapshot=evidence_snapshot,
            output=output,
        )
        self.session.add(recommendation)
        self.session.commit()
        self.session.refresh(recommendation)
        return recommendation
