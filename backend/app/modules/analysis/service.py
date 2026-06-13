from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import SessionLocal
from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.remote_sensing import get_remote_sensing_provider
from app.modules.analysis.repository import AnalysisRepository
from app.modules.climate.provider import get_climate_provider
from app.modules.risk.scoring import score_risks


class AnalysisService:
    def __init__(self, repository: AnalysisRepository):
        self.repository = repository

    def start_analysis(self, farm_id: UUID, owner_id: UUID) -> FarmAnalysis:
        farm = self.repository.get_farm_for_owner(farm_id=farm_id, owner_id=owner_id)
        if not farm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
        return self.repository.create(farm_id=farm_id)

    def get_analysis(self, analysis_id: UUID, owner_id: UUID) -> FarmAnalysis:
        analysis = self.repository.get_for_owner(analysis_id=analysis_id, owner_id=owner_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return analysis


def run_analysis_job(analysis_id: UUID) -> None:
    with SessionLocal() as session:
        repository = AnalysisRepository(session)
        analysis = repository.get(analysis_id)
        if not analysis:
            return

        farm = repository.get_farm(analysis.farm_id)
        boundary_wkt = repository.get_boundary_wkt(analysis.farm_id)
        if not farm or not boundary_wkt:
            repository.mark_failed(analysis_id, "Farm boundary not found")
            return

        try:
            result = get_remote_sensing_provider().analyze(farm=farm, boundary_wkt=boundary_wkt)
            climate_summary = get_climate_provider().summarize(farm=farm, boundary_wkt=boundary_wkt)
        except Exception as exc:
            repository.mark_failed(analysis_id, str(exc))
            return

        analysis.ndvi = result.ndvi
        analysis.water_stress = result.water_stress
        analysis.rainfall_anomaly_percent = climate_summary.rainfall_anomaly_percent
        analysis.rainfall_this_season_mm = climate_summary.rainfall_this_season_mm
        analysis.temperature_anomaly_c = climate_summary.temperature_anomaly_c
        risk_assessment = score_risks(farm=farm, analysis=analysis)

        repository.mark_completed(analysis_id, result, climate_summary, risk_assessment)
