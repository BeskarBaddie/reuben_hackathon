from datetime import date
from uuid import uuid4

from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm, IrrigationType
from app.modules.recommendations.service import (
    build_evidence_snapshot,
    generate_deterministic_recommendations,
)


def test_deterministic_recommendations_prioritize_high_drought() -> None:
    farm = Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Field A",
        crop="maize",
        planting_date=date(2026, 5, 1),
        irrigation_type=IrrigationType.RAINFED,
        area_hectares=2.4,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
    )
    analysis = FarmAnalysis(
        id=uuid4(),
        farm_id=farm.id,
        status=AnalysisStatus.COMPLETED,
        ndvi=0.1,
        vegetation_health="stressed",
        water_stress="high",
        rainfall_anomaly_percent=-41,
        drought_score=100,
        drought_level="high",
        drought_drivers=[
            "Rainfall is 41% below historical average",
            "NDVI indicates severe vegetation stress",
        ],
        flood_score=0,
        flood_level="low",
        heat_score=17,
        heat_level="low",
        overall_risk_level="high",
    )

    output = generate_deterministic_recommendations(build_evidence_snapshot(farm, analysis))

    assert output["actions"][0]["priority"] == 1
    assert "Mulch" in output["actions"][0]["action"]
    assert output["actions"][0]["evidence"]
