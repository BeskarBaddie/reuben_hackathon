from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.remote_sensing import RemoteSensingResult
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.climate.schemas import ClimateSummary
from app.modules.farms.models import Farm
from app.modules.risk.schemas import RiskAssessment


class AnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, farm_id: UUID) -> FarmAnalysis:
        analysis = FarmAnalysis(farm_id=farm_id, status=AnalysisStatus.PROCESSING)
        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def get(self, analysis_id: UUID) -> FarmAnalysis | None:
        return self.session.get(FarmAnalysis, analysis_id)

    def get_for_owner(self, analysis_id: UUID, owner_id: UUID) -> FarmAnalysis | None:
        statement = (
            select(FarmAnalysis)
            .join(Farm, Farm.id == FarmAnalysis.farm_id)
            .where(FarmAnalysis.id == analysis_id, Farm.owner_id == owner_id)
        )
        return self.session.scalars(statement).first()

    def get_farm_for_owner(self, farm_id: UUID, owner_id: UUID) -> Farm | None:
        statement = select(Farm).where(Farm.id == farm_id, Farm.owner_id == owner_id)
        return self.session.scalars(statement).first()

    def get_farm(self, farm_id: UUID) -> Farm | None:
        return self.session.get(Farm, farm_id)

    def get_boundary_wkt(self, farm_id: UUID) -> str | None:
        if settings.database_url.startswith("sqlite"):
            farm = self.get_farm(farm_id)
            return str(farm.boundary) if farm else None

        statement = select(func.ST_AsText(Farm.boundary)).where(Farm.id == farm_id)
        return self.session.execute(statement).scalar_one_or_none()

    def mark_completed(
        self,
        analysis_id: UUID,
        result: RemoteSensingResult,
        climate_summary: ClimateSummary | None = None,
        risk_assessment: RiskAssessment | None = None,
    ) -> None:
        analysis = self.get(analysis_id)
        if not analysis:
            return
        analysis.status = AnalysisStatus.COMPLETED
        analysis.ndvi = result.ndvi
        analysis.vegetation_health = result.vegetation_health
        analysis.vegetation_trend = result.vegetation_trend
        analysis.water_stress = result.water_stress
        analysis.image_date = result.image_date
        analysis.source = result.source
        analysis.evidence = result.evidence
        if climate_summary:
            analysis.climate_season_start = climate_summary.season_start
            analysis.climate_season_end = climate_summary.season_end
            analysis.rainfall_this_season_mm = climate_summary.rainfall_this_season_mm
            analysis.rainfall_historical_average_mm = (
                climate_summary.rainfall_historical_average_mm
            )
            analysis.rainfall_anomaly_percent = climate_summary.rainfall_anomaly_percent
            analysis.temperature_this_season_c = climate_summary.temperature_this_season_c
            analysis.temperature_historical_average_c = (
                climate_summary.temperature_historical_average_c
            )
            analysis.temperature_anomaly_c = climate_summary.temperature_anomaly_c
            analysis.climate_signal = climate_summary.climate_signal
            analysis.climate_source = climate_summary.source
            analysis.climate_evidence = climate_summary.evidence
        if risk_assessment:
            analysis.drought_score = risk_assessment.drought.score
            analysis.drought_level = risk_assessment.drought.level
            analysis.drought_drivers = risk_assessment.drought.drivers
            analysis.flood_score = risk_assessment.flood.score
            analysis.flood_level = risk_assessment.flood.level
            analysis.flood_drivers = risk_assessment.flood.drivers
            analysis.heat_score = risk_assessment.heat.score
            analysis.heat_level = risk_assessment.heat.level
            analysis.heat_drivers = risk_assessment.heat.drivers
            analysis.overall_risk_level = risk_assessment.overall_level
        analysis.error_message = None
        self.session.commit()

    def mark_failed(self, analysis_id: UUID, message: str) -> None:
        analysis = self.get(analysis_id)
        if not analysis:
            return
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = message
        self.session.commit()
