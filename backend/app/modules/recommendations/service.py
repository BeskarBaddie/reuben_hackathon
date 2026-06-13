import json
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm
from app.modules.recommendations.prompts import (
    PROMPT_VERSION,
    RECOMMENDATION_JSON_SCHEMA,
    RECOMMENDATION_SYSTEM_PROMPT,
    build_recommendation_context,
)
from app.modules.recommendations.repository import RecommendationRepository
from app.modules.recommendations.schemas import RecommendationOutput


class RecommendationService:
    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    def get_latest(self, analysis_id: UUID, owner_id: UUID):
        analysis = self.repository.get_analysis_for_owner(analysis_id, owner_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        recommendation = self.repository.latest_for_analysis(analysis_id)
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found",
            )
        return recommendation

    def generate(self, analysis_id: UUID, owner_id: UUID):
        analysis = self.repository.get_analysis_for_owner(analysis_id, owner_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        if analysis.status != AnalysisStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis must be completed before recommendations can be generated",
            )

        farm = self.repository.get_farm(analysis.farm_id)
        if not farm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

        evidence = build_evidence_snapshot(farm, analysis)
        provider = "deterministic"
        model = None
        output = generate_deterministic_recommendations(evidence)

        if settings.recommendation_provider == "openai" and settings.openai_api_key:
            try:
                output = generate_openai_recommendations(evidence)
                provider = "openai"
                model = settings.openai_model
            except Exception:
                provider = "deterministic_fallback"
                model = settings.openai_model
        elif settings.recommendation_provider == "ollama":
            try:
                output = generate_ollama_recommendations(evidence)
                provider = "ollama"
                model = settings.ollama_model
            except Exception:
                provider = "deterministic_fallback"
                model = settings.ollama_model

        validated = RecommendationOutput.model_validate(output).model_dump()
        return self.repository.create(
            analysis_id=analysis_id,
            provider=provider,
            model=model,
            prompt_version=PROMPT_VERSION,
            evidence_snapshot=evidence,
            output=validated,
        )


def build_evidence_snapshot(farm: Farm, analysis: FarmAnalysis) -> dict:
    return {
        "farm": {
            "id": str(farm.id),
            "name": farm.name,
            "crop": farm.crop,
            "area_hectares": farm.area_hectares,
            "planting_date": farm.planting_date.isoformat() if farm.planting_date else None,
            "expected_harvest_date": (
                farm.expected_harvest_date.isoformat() if farm.expected_harvest_date else None
            ),
            "irrigation_type": farm.irrigation_type.value,
            "farmer_notes": farm.notes or "insufficient data",
        },
        "vegetation": {
            "ndvi": analysis.ndvi,
            "vegetation_health": analysis.vegetation_health,
            "water_stress": analysis.water_stress,
            "image_date": analysis.image_date,
            "source": analysis.source,
        },
        "climate": {
            "season_start": analysis.climate_season_start,
            "season_end": analysis.climate_season_end,
            "rainfall_this_season_mm": analysis.rainfall_this_season_mm,
            "rainfall_historical_average_mm": analysis.rainfall_historical_average_mm,
            "rainfall_anomaly_percent": analysis.rainfall_anomaly_percent,
            "temperature_this_season_c": analysis.temperature_this_season_c,
            "temperature_anomaly_c": analysis.temperature_anomaly_c,
            "climate_signal": analysis.climate_signal,
        },
        "risk": {
            "drought_score": analysis.drought_score,
            "drought_level": analysis.drought_level,
            "drought_drivers": analysis.drought_drivers or [],
            "flood_score": analysis.flood_score,
            "flood_level": analysis.flood_level,
            "flood_drivers": analysis.flood_drivers or [],
            "heat_score": analysis.heat_score,
            "heat_level": analysis.heat_level,
            "heat_drivers": analysis.heat_drivers or [],
            "overall_risk_level": analysis.overall_risk_level,
        },
    }


def generate_deterministic_recommendations(evidence: dict) -> dict:
    risk = evidence["risk"]
    farm = evidence["farm"]
    actions: list[dict] = []

    if risk["drought_level"] == "high":
        actions.extend(
            [
                {
                    "priority": 1,
                    "action": "Mulch exposed soil around the crop",
                    "reason": "Mulch reduces evaporation and helps keep moisture in the root zone.",
                    "evidence": risk["drought_drivers"][:2] or ["Drought risk is high"],
                },
                {
                    "priority": 2,
                    "action": "Prioritize any available irrigation for the most stressed parts of the field",
                    "reason": "Targeted watering protects the crop when rainfall is well below normal.",
                    "evidence": risk["drought_drivers"][:2] or ["Water stress risk is high"],
                },
                {
                    "priority": 3,
                    "action": "Delay fertilizer application until soil moisture improves",
                    "reason": "Fertilizer is less effective and can damage crops when the soil is too dry.",
                    "evidence": risk["drought_drivers"][:2] or ["Vegetation stress is present"],
                },
            ]
        )

    if risk["flood_level"] in {"medium", "high"}:
        actions.append(
            {
                "priority": len(actions) + 1,
                "action": "Clear drainage channels before the next heavy rainfall",
                "reason": "Improving water flow reduces standing water around crop roots.",
                "evidence": risk["flood_drivers"][:2] or ["Flood risk is elevated"],
            }
        )

    if risk["heat_level"] in {"medium", "high"}:
        actions.append(
            {
                "priority": len(actions) + 1,
                "action": "Avoid spraying or fertilizer application during the hottest part of the day",
                "reason": "Heat can increase crop stress and reduce input effectiveness.",
                "evidence": risk["heat_drivers"][:2] or ["Heat stress risk is elevated"],
            }
        )

    if not actions:
        actions.append(
            {
                "priority": 1,
                "action": "Continue monitoring crop condition weekly",
                "reason": "Current risk indicators do not show an urgent climate threat.",
                "evidence": ["Overall risk level is low"],
            }
        )

    for index, action in enumerate(actions[:6], start=1):
        action["priority"] = index

    return {
        "summary": (
            f"{farm['name']} has {risk['overall_risk_level'] or 'insufficient data'} overall risk. "
            f"The main concern is drought risk for {farm['crop']}."
            if risk["drought_level"] == "high"
            else f"{farm['name']} has {risk['overall_risk_level'] or 'insufficient data'} overall risk based on the latest analysis."
        ),
        "actions": actions[:6],
    }


def generate_openai_recommendations(evidence: dict) -> dict:
    context = build_recommendation_context(evidence)
    compact_evidence = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    payload = {
        "model": settings.openai_model,
        "input": [
            {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"Agricultural context for this request:\n{context}",
            },
            {
                "role": "user",
                "content": (
                    "Generate farmer-friendly adaptation recommendations from this evidence. "
                    "Use only the evidence fields provided. Keep actions concise and directly tied to evidence.\n\n"
                    f"{compact_evidence}"
                ),
            },
        ],
        "max_output_tokens": 900,
        "prompt_cache_key": f"recommendations:{PROMPT_VERSION}:{settings.openai_model}",
        "text": {
            "format": {
                "type": "json_schema",
                "name": "farm_recommendations",
                "schema": RECOMMENDATION_JSON_SCHEMA,
                "strict": True,
            }
        },
    }

    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")
                    break
            if text:
                break
    if not text:
        raise RuntimeError("OpenAI response did not contain output text")
    return json.loads(text)


def generate_ollama_recommendations(evidence: dict) -> dict:
    context = build_recommendation_context(evidence)
    compact_evidence = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    response = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        json={
            "model": settings.ollama_model,
            "stream": False,
            "format": RECOMMENDATION_JSON_SCHEMA,
            "messages": [
                {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                {
                    "role": "system",
                    "content": f"Agricultural context for this request:\n{context}",
                },
                {
                    "role": "user",
                    "content": (
                        "Generate farmer-friendly adaptation recommendations from this evidence. "
                        "Use only the evidence fields provided. Return only JSON.\n\n"
                        f"{compact_evidence}"
                    ),
                },
            ],
            "options": {
                "temperature": 0.2,
                "num_predict": 900,
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content")
    if not content:
        raise RuntimeError("Ollama response did not contain message content")
    return json.loads(content)
