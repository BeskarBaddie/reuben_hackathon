RECOMMENDATION_SYSTEM_PROMPT = """
You write farmer-friendly climate adaptation recommendations from provided evidence only.
Return JSON only. Never invent measurements, risks, crops, locations, prices, dates, pests, diseases, or inputs.
If evidence is missing, say "insufficient data" for the affected field.
Do not calculate NDVI, climate anomalies, geospatial metrics, or risk scores.
Treat risk scores, climate summaries, vegetation indicators, crop, irrigation, planting date, and farmer notes as evidence.
When retrieved_guidance is provided, extract practical agronomic actions from it and cite the source_name in action evidence.
Use the agricultural context only as general guidance. Prefer low-cost, climate-resilient actions for smallholder farmers.
Make each action specific to the farm evidence, especially crop, irrigation type, planting/harvest timing, current risks, and farmer observations.
Avoid generic action labels. Include concrete timing, location within the plot, crop stage, trigger, or operating condition when evidence supports it.
Consider these decision types when evidence supports them: soil moisture conservation, fertilizer timing, targeted irrigation, drainage, planting-date adjustment for the next season, crop area allocation, crop/variety choice, planting higher or lower parts of the plot, erosion control, and harvest timing.
For planting-date shifts, planting more/less of a crop, or using higher ground, only recommend them when supported by risk/climate evidence, farmer notes, forecast/season context, or retrieved guidance. Otherwise say "insufficient data" rather than guessing.
Do not recommend restricted chemicals, prescription products, or unsafe handling practices.
""".strip()

PROMPT_VERSION = "recommendations.v3"

GENERAL_CONTEXT = """
General smallholder guidance:
- Prioritize actions that reduce downside risk quickly, require limited cash, and can be explained simply.
- Prefer climate-resilient phrasing: protect soil cover, reduce water loss, keep options open, avoid exposing the farmer to unnecessary input risk, and protect the most vulnerable crop stage.
- For drought: conserve soil moisture, reduce evaporation, protect roots, prioritize scarce irrigation, weed early to reduce water competition, and avoid applying fertilizer into dry soil.
- For flood: improve drainage, avoid field traffic on saturated soil, plant or replant vulnerable crops on higher ground when flood evidence supports it, protect seed and fertilizer from runoff, and watch for root stress after standing water.
- For heat stress: avoid spraying or fertilizer application during peak heat, irrigate early morning when available, and reduce avoidable crop stress.
- For timing decisions: use the current planting date, expected harvest date, crop stage, rainfall anomaly, forecast/climate signal, and retrieved guidance. If those do not support a specific change, say "insufficient data".
- For crop allocation decisions: only advise planting more or less of a crop when evidence shows persistent drought/flood/heat risk or retrieved guidance supports an alternative. Frame it as next-season planning unless the current season can still be changed.
- Use "insufficient data" when the evidence does not support a specific timing, input, or field operation.
""".strip()

CROP_CONTEXT = {
    "maize": """
Crop context for maize:
- Maize is sensitive to moisture stress around tasseling, silking, and early grain fill.
- If drought risk is high, prioritize soil moisture conservation and irrigation during flowering stages when possible.
- Nitrogen application is more useful when soil moisture is adequate; avoid top-dressing immediately before likely heavy rain.
- For rainfed maize under strong drought evidence, next-season options can include shifting planting closer to reliable rainfall onset, reducing maize area on the driest section, or using the lower-moisture-loss part of the plot, but only if the evidence supports that advice.
""".strip(),
    "rice": """
Crop context for rice:
- Rice water needs depend on production system; do not assume flooded paddy unless evidence says so.
- For flood risk, distinguish controlled standing water from damaging runoff or prolonged submergence.
- For water stress, prioritize maintaining soil moisture during establishment, tillering, and flowering.
- If flood or waterlogging evidence is high, consider higher or better-drained sections for non-paddy rice only when the production system and field evidence support it.
""".strip(),
    "sorghum": """
Crop context for sorghum:
- Sorghum is more drought tolerant than maize but still loses yield under severe moisture stress near flowering.
- Moisture conservation and timely weeding can reduce competition for limited water.
""".strip(),
    "beans": """
Crop context for beans:
- Beans are sensitive to waterlogging and moisture stress during flowering and pod filling.
- For flood risk, drainage and avoiding saturated soil disturbance are high-priority actions.
""".strip(),
}

IRRIGATION_CONTEXT = {
    "none": "Irrigation context: no irrigation is available, so recommendations should focus on rainfall timing, soil moisture conservation, drainage, crop management, and low-cost practices.",
    "rainfed": "Irrigation context: the farm is rainfed, so recommendations should not assume the farmer can irrigate. If mentioning water, frame it as only if limited water is available.",
    "partial": "Irrigation context: partial irrigation is available. Recommend targeted irrigation only for the highest-stress areas or most sensitive crop stages.",
    "full": "Irrigation context: full irrigation is available. Recommend scheduling and prioritization, but still avoid waste and waterlogging.",
}


def build_recommendation_context(evidence: dict) -> str:
    farm = evidence.get("farm", {})
    risk = evidence.get("risk", {})
    crop = str(farm.get("crop") or "").strip().lower()
    irrigation_type = str(farm.get("irrigation_type") or "").strip().lower()

    sections = [GENERAL_CONTEXT]

    for crop_key, context in CROP_CONTEXT.items():
        if crop_key in crop:
            sections.append(context)
            break

    irrigation_context = IRRIGATION_CONTEXT.get(irrigation_type)
    if irrigation_context:
        sections.append(irrigation_context)

    if risk.get("overall_risk_level") in {None, "insufficient data"}:
        sections.append(
            "Risk context: if overall risk is missing, keep recommendations conservative and explain which evidence is insufficient."
        )

    return "\n\n".join(sections)

RECOMMENDATION_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "actions"],
    "properties": {
        "summary": {"type": "string"},
        "actions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["priority", "action", "reason", "evidence"],
                "properties": {
                    "priority": {"type": "integer", "minimum": 1, "maximum": 6},
                    "action": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                },
            },
        },
    },
}
