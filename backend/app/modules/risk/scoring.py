from datetime import UTC, date, datetime

from app.modules.analysis.models import FarmAnalysis
from app.modules.farms.models import Farm, IrrigationType
from app.modules.risk.schemas import RiskAssessment, RiskScore


def score_risks(farm: Farm, analysis: FarmAnalysis) -> RiskAssessment:
    drought = _score_drought(farm, analysis)
    flood = _score_flood(analysis)
    heat = _score_heat(farm, analysis)
    overall_level = _max_level([drought.level, flood.level, heat.level])

    return RiskAssessment(
        drought=drought,
        flood=flood,
        heat=heat,
        overall_level=overall_level,
    )


def _score_drought(farm: Farm, analysis: FarmAnalysis) -> RiskScore:
    score = 0
    drivers: list[str] = []

    if analysis.rainfall_anomaly_percent is not None:
        if analysis.rainfall_anomaly_percent <= -40:
            score += 40
            drivers.append(
                f"Rainfall is {abs(analysis.rainfall_anomaly_percent):.0f}% below historical average"
            )
        elif analysis.rainfall_anomaly_percent <= -25:
            score += 28
            drivers.append(
                f"Rainfall is {abs(analysis.rainfall_anomaly_percent):.0f}% below historical average"
            )
        elif analysis.rainfall_anomaly_percent <= -10:
            score += 12
            drivers.append("Rainfall is moderately below historical average")

    if analysis.ndvi is not None:
        if analysis.ndvi < 0.25:
            score += 25
            drivers.append("NDVI indicates severe vegetation stress")
        elif analysis.ndvi < 0.42:
            score += 16
            drivers.append("NDVI indicates vegetation stress")

    if analysis.water_stress == "high":
        score += 20
        drivers.append("Water stress indicator is high")
    elif analysis.water_stress == "medium":
        score += 10
        drivers.append("Water stress indicator is medium")

    if farm.irrigation_type in {IrrigationType.RAINFED, IrrigationType.NONE}:
        score += 15
        drivers.append("Farm has limited irrigation protection")
    elif farm.irrigation_type == IrrigationType.PARTIAL:
        score += 7
        drivers.append("Farm has only partial irrigation protection")

    if not drivers:
        drivers.append("No strong drought stress drivers detected")

    return RiskScore(score=min(score, 100), level=_level(score), drivers=drivers)


def _score_flood(analysis: FarmAnalysis) -> RiskScore:
    score = 0
    drivers: list[str] = []

    if analysis.rainfall_anomaly_percent is not None:
        if analysis.rainfall_anomaly_percent >= 50:
            score += 50
            drivers.append("Rainfall is far above historical average")
        elif analysis.rainfall_anomaly_percent >= 25:
            score += 32
            drivers.append("Rainfall is above historical average")
        elif analysis.rainfall_anomaly_percent >= 10:
            score += 15
            drivers.append("Rainfall is slightly above historical average")

    if analysis.rainfall_this_season_mm is not None:
        if analysis.rainfall_this_season_mm >= 700:
            score += 25
            drivers.append("Seasonal rainfall total is very high")
        elif analysis.rainfall_this_season_mm >= 500:
            score += 12
            drivers.append("Seasonal rainfall total is elevated")

    if not drivers:
        drivers.append("No strong excess rainfall drivers detected")

    return RiskScore(score=min(score, 100), level=_level(score), drivers=drivers)


def _score_heat(farm: Farm, analysis: FarmAnalysis) -> RiskScore:
    score = 0
    drivers: list[str] = []

    if analysis.temperature_anomaly_c is not None:
        if analysis.temperature_anomaly_c >= 2.5:
            score += 45
            drivers.append(
                f"Temperature is {analysis.temperature_anomaly_c:.1f} C above historical average"
            )
        elif analysis.temperature_anomaly_c >= 1.5:
            score += 30
            drivers.append(
                f"Temperature is {analysis.temperature_anomaly_c:.1f} C above historical average"
            )
        elif analysis.temperature_anomaly_c >= 0.8:
            score += 14
            drivers.append("Temperature is moderately above historical average")

    if analysis.ndvi is not None and analysis.ndvi < 0.35:
        score += 12
        drivers.append("Vegetation stress can increase heat vulnerability")

    if farm.planting_date and _days_since(farm.planting_date) <= 75:
        score += 10
        drivers.append("Crop may be in an early growth stage")

    if farm.crop.lower() in {"maize", "corn", "beans", "rice"}:
        score += 5
        drivers.append(f"{farm.crop} can be sensitive to heat during key growth stages")

    if not drivers:
        drivers.append("No strong heat stress drivers detected")

    return RiskScore(score=min(score, 100), level=_level(score), drivers=drivers)


def _level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _max_level(levels: list[str]) -> str:
    priority = {"low": 0, "medium": 1, "high": 2}
    return max(levels, key=lambda level: priority[level])


def _days_since(value: date) -> int:
    return (datetime.now(UTC).date() - value).days
