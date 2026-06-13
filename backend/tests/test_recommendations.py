from datetime import date
from uuid import uuid4

from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm, IrrigationType
from app.modules.recommendations.service import (
    build_evidence_snapshot,
    generate_deterministic_recommendations,
)
from app.modules.recommendations.prompts import build_recommendation_context


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
        notes="Farmer says the top end of the field dries first and water access is limited.",
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


def test_evidence_snapshot_includes_farmer_notes() -> None:
    farm = Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Field B",
        crop="maize",
        planting_date=date(2026, 5, 1),
        expected_harvest_date=date(2026, 9, 1),
        irrigation_type=IrrigationType.PARTIAL,
        area_hectares=1.8,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        notes="Low area floods after heavy rain; upper slope is sandy.",
    )
    analysis = FarmAnalysis(
        id=uuid4(),
        farm_id=farm.id,
        status=AnalysisStatus.COMPLETED,
        overall_risk_level="medium",
    )

    evidence = build_evidence_snapshot(farm, analysis)

    assert evidence["farm"]["farmer_notes"] == "Low area floods after heavy rain; upper slope is sandy."
    assert evidence["farm"]["expected_harvest_date"] == "2026-09-01"


def test_recommendation_context_selects_relevant_crop_and_irrigation_only() -> None:
    evidence = {
        "farm": {"crop": "maize", "irrigation_type": "partial"},
        "risk": {"overall_risk_level": "high"},
    }

    context = build_recommendation_context(evidence)

    assert "Crop context for maize" in context
    assert "partial irrigation is available" in context
    assert "Crop context for rice" not in context
