from dataclasses import dataclass


RiskLevel = str


@dataclass(frozen=True)
class RiskScore:
    score: int
    level: RiskLevel
    drivers: list[str]


@dataclass(frozen=True)
class RiskAssessment:
    drought: RiskScore
    flood: RiskScore
    heat: RiskScore
    overall_level: RiskLevel
