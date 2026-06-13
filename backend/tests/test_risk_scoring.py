from datetime import date
from uuid import uuid4

from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm, IrrigationType
from app.modules.risk.scoring import score_risks


def make_farm(irrigation_type: IrrigationType = IrrigationType.RAINFED) -> Farm:
    return Farm(
        id=uuid4(),
        owner_id=uuid4(),
        name="Test Farm",
        crop="maize",
        planting_date=date(2026, 5, 1),
        irrigation_type=irrigation_type,
        area_hectares=2.0,
        boundary="POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
    )


def make_analysis(**overrides) -> FarmAnalysis:
    values = {
        "id": uuid4(),
        "farm_id": uuid4(),
        "status": AnalysisStatus.COMPLETED,
        "ndvi": 0.5,
        "water_stress": "low",
        "rainfall_anomaly_percent": 0,
        "rainfall_this_season_mm": 300,
        "temperature_anomaly_c": 0,
    }
    values.update(overrides)
    return FarmAnalysis(**values)


def test_scores_high_drought_for_dry_stressed_rainfed_farm() -> None:
    assessment = score_risks(
        make_farm(irrigation_type=IrrigationType.RAINFED),
        make_analysis(ndvi=0.18, water_stress="high", rainfall_anomaly_percent=-41),
    )

    assert assessment.drought.level == "high"
    assert assessment.drought.score >= 70
    assert any("Rainfall" in driver for driver in assessment.drought.drivers)


def test_scores_high_flood_for_extreme_positive_rainfall_anomaly() -> None:
    assessment = score_risks(
        make_farm(),
        make_analysis(rainfall_anomaly_percent=55, rainfall_this_season_mm=720),
    )

    assert assessment.flood.level == "high"
    assert assessment.flood.score >= 70


def test_scores_medium_heat_for_hot_stressed_crop() -> None:
    assessment = score_risks(
        make_farm(),
        make_analysis(temperature_anomaly_c=1.8, ndvi=0.3),
    )

    assert assessment.heat.level == "medium"
    assert assessment.heat.score >= 40
