import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.knowledge.repository import KnowledgeRepository


STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "this",
    "that",
    "plot",
    "farm",
    "risk",
    "score",
    "level",
    "insufficient",
    "data",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def build_retrieval_query(evidence: dict) -> str:
    farm = evidence.get("farm", {})
    risk = evidence.get("risk", {})
    climate = evidence.get("climate", {})
    vegetation = evidence.get("vegetation", {})
    parts = [
        farm.get("crop"),
        farm.get("irrigation_type"),
        farm.get("farmer_notes"),
        climate.get("climate_signal"),
        vegetation.get("vegetation_health"),
        vegetation.get("water_stress"),
        risk.get("overall_risk_level"),
        f"drought {risk.get('drought_level') or ''}",
        f"flood {risk.get('flood_level') or ''}",
        f"heat {risk.get('heat_level') or ''}",
        " ".join(risk.get("drought_drivers") or []),
        " ".join(risk.get("flood_drivers") or []),
        " ".join(risk.get("heat_drivers") or []),
    ]
    return " ".join(str(part) for part in parts if part)


def retrieve_guidance_for_evidence(
    session: Session,
    evidence: dict,
    limit: int | None = None,
) -> list[dict]:
    farm = evidence.get("farm", {})
    crop = str(farm.get("crop") or "").strip().lower() or None
    query_terms = tokenize(build_retrieval_query(evidence))
    if not query_terms:
        return []

    repository = KnowledgeRepository(session)
    candidates = repository.candidate_chunks(crop=crop, limit=250)
    scored: list[tuple[float, object]] = []
    for chunk in candidates:
        chunk_terms = tokenize(chunk.text)
        overlap = query_terms & chunk_terms
        if not overlap:
            continue
        score = float(len(overlap))
        if crop and chunk.crop == crop:
            score += 3.0
        if chunk.topic and chunk.topic in query_terms:
            score += 2.0
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk in scored[: limit or settings.knowledge_max_chunks]:
        results.append(
            {
                "source_name": chunk.source_name,
                "source_url": chunk.source_url,
                "crop": chunk.crop,
                "topic": chunk.topic,
                "text": chunk.text[:1600],
                "score": score,
            }
        )
    return results
