import json
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.analysis.models import FarmAnalysis
from app.modules.analysis.schemas import AnalysisStatus
from app.modules.farms.models import Farm
from app.modules.recommendations.forecast import build_forecast
from app.modules.recommendations.prompts import (
    PROMPT_VERSION,
    RECOMMENDATION_JSON_SCHEMA,
    RECOMMENDATION_SYSTEM_PROMPT,
)
from app.modules.recommendations.repository import RecommendationRepository
from app.modules.recommendations.retrieval import (
    RetrievedPassage,
    citations_from_passages,
    format_context,
    retrieve,
)
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

        # Retrieve grounding guidance from the local document corpus.
        passages = retrieve(evidence)
        context = format_context(passages)

        provider = "deterministic"
        model = None
        output = generate_deterministic_recommendations(evidence, passages)

        if settings.recommendation_provider == "openai" and settings.openai_api_key:
            try:
                output = generate_openai_recommendations(evidence, context)
                provider = "openai"
                model = settings.openai_model
            except Exception:
                output = generate_deterministic_recommendations(evidence, passages)
                provider = "deterministic_fallback"
                model = settings.openai_model
        elif settings.recommendation_provider == "ollama":
            try:
                output = generate_ollama_recommendations(evidence, context)
                provider = "ollama"
                model = settings.ollama_model
            except Exception:
                output = generate_deterministic_recommendations(evidence, passages)
                provider = "deterministic_fallback"
                model = settings.ollama_model

        # Citations are derived from the passages actually retrieved, never from the
        # model, so they cannot be fabricated.
        output["citations"] = citations_from_passages(passages)
        validated = RecommendationOutput.model_validate(output).model_dump()

        # Record what was retrieved so the recommendation is auditable.
        evidence["retrieval"] = {
            "passages": [
                {
                    "doc_id": passage.doc_id,
                    "title": passage.title,
                    "source": passage.source,
                    "score": passage.score,
                }
                for passage in passages
            ],
        }

        return self.repository.create(
            analysis_id=analysis_id,
            provider=provider,
            model=model,
            prompt_version=PROMPT_VERSION,
            evidence_snapshot=evidence,
            output=validated,
        )


def build_evidence_snapshot(farm: Farm, analysis: FarmAnalysis) -> dict:
    climate = {
        "season_start": analysis.climate_season_start,
        "season_end": analysis.climate_season_end,
        "rainfall_this_season_mm": analysis.rainfall_this_season_mm,
        "rainfall_historical_average_mm": analysis.rainfall_historical_average_mm,
        "rainfall_anomaly_percent": analysis.rainfall_anomaly_percent,
        "temperature_this_season_c": analysis.temperature_this_season_c,
        "temperature_historical_average_c": getattr(
            analysis, "temperature_historical_average_c", None
        ),
        "temperature_anomaly_c": analysis.temperature_anomaly_c,
        "climate_signal": analysis.climate_signal,
    }
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
        "climate": climate,
        "forecast": build_forecast(farm, climate),
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


def _forecast_summary(forecast: dict) -> str:
    if not forecast:
        return "There is insufficient data for a near-term weather forecast."
    signal = forecast.get("forecast_signal") or "insufficient data"
    if signal == "insufficient data":
        return "There is insufficient data for a near-term weather forecast."
    horizon = forecast.get("horizon_days")
    text = f"Over the next {horizon} days the outlook is {signal}"
    rain = forecast.get("rainfall_outlook_mm")
    rain_pct = forecast.get("rainfall_outlook_percent")
    if rain is not None and rain_pct is not None:
        text += f", with about {rain} mm of rain ({rain_pct:+.0f}% versus normal)"
    temperature = forecast.get("temperature_outlook_c")
    if temperature is not None:
        text += f", and average temperatures near {temperature} degrees Celsius"
    return text + "."


def _deterministic_narrative(
    evidence: dict,
    actions: list[dict],
    passages: list[RetrievedPassage],
    forecast_summary: str,
) -> str:
    farm = evidence["farm"]
    risk = evidence["risk"]
    overall = risk.get("overall_risk_level") or "insufficient data"

    narrative = (
        f"For {farm['name']} growing {farm['crop']}, the latest analysis points to "
        f"{overall} overall climate risk."
    )

    concerns = [
        hazard
        for hazard in ("drought", "flood", "heat")
        if str(risk.get(f"{hazard}_level") or "").lower() in {"medium", "high"}
    ]
    if concerns:
        narrative += f" The main concern is {concerns[0]} risk."
    else:
        narrative += " No single hazard stands out as urgent right now."

    if actions:
        first = actions[0]["action"]
        narrative += f" The most important step is to {first[0].lower()}{first[1:]}."

    narrative += f" {forecast_summary}"

    if passages:
        titles = "; ".join(passage.title for passage in passages[:2])
        narrative += f" This guidance draws on: {titles}."

    return narrative


def generate_deterministic_recommendations(
    evidence: dict, passages: list[RetrievedPassage] | None = None
) -> dict:
    passages = passages or []
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

    actions = actions[:6]

    summary = (
        f"{farm['name']} has {risk['overall_risk_level'] or 'insufficient data'} overall risk. "
        f"The main concern is drought risk for {farm['crop']}."
        if risk["drought_level"] == "high"
        else f"{farm['name']} has {risk['overall_risk_level'] or 'insufficient data'} overall risk based on the latest analysis."
    )
    forecast_summary = _forecast_summary(evidence.get("forecast", {}))

    return {
        "summary": summary,
        "narrative": _deterministic_narrative(evidence, actions, passages, forecast_summary),
        "forecast_summary": forecast_summary,
        "actions": actions,
    }


def generate_openai_recommendations(evidence: dict, context: str) -> dict:
    compact_evidence = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    payload = {
        "model": settings.openai_model,
        "input": [
            {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"Retrieved guidance passages for this request:\n{context}",
            },
            {
                "role": "user",
                "content": (
                    "Generate farmer-friendly adaptation recommendations from this evidence. "
                    "Use only the evidence fields and the retrieved guidance passages. "
                    "Keep actions concise and directly tied to evidence, and include the prose narrative "
                    "and forecast summary.\n\n"
                    f"{compact_evidence}"
                ),
            },
        ],
        "max_output_tokens": 1100,
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


def generate_ollama_recommendations(evidence: dict, context: str) -> dict:
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
                    "content": f"Retrieved guidance passages for this request:\n{context}",
                },
                {
                    "role": "user",
                    "content": (
                        "Generate farmer-friendly adaptation recommendations from this evidence. "
                        "Use only the evidence fields and the retrieved guidance passages. "
                        "Return only JSON with the prose narrative and forecast summary.\n\n"
                        f"{compact_evidence}"
                    ),
                },
            ],
            "keep_alive": "30m",
            "options": {
                "temperature": 0.2,
                "num_predict": 1100,
            },
        },
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content")
    if not content:
        raise RuntimeError("Ollama response did not contain message content")
    return json.loads(content)
