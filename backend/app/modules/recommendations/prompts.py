"""Prompt text and output schema for the recommendation engine.

Grounding context is no longer hardcoded here. It is retrieved at request time
from the local document corpus (see ``retrieval.py``) and passed to the model as
guidance passages. This module only owns the instruction text and the structured
output contract.
"""

PROMPT_VERSION = "recommendations.v6"

RECOMMENDATION_SYSTEM_PROMPT = """
You write farmer-friendly climate adaptation recommendations from provided evidence only.
Return JSON only. Never invent measurements, risks, crops, locations, prices, dates, pests, diseases, or inputs.
If evidence is missing, say "insufficient data" for the affected field.
Do not calculate NDVI, climate anomalies, geospatial metrics, risk scores, or the forecast.
Treat risk scores, climate summaries, the forecast, vegetation indicators, crop, irrigation, planting date,
expected harvest date, and farmer notes as evidence.
Use the retrieved guidance passages as your source of agronomic knowledge; do not contradict them and do not
add agronomic claims that are not supported by the evidence or the passages.
Prefer low-cost, practical actions for smallholder farmers, and make each action specific to this farm's
evidence, especially crop, irrigation type, current risks, the forecast, and farmer observations.
Do not recommend restricted chemicals, prescription products, or unsafe handling practices.

Produce:
- "summary": one or two sentences naming the overall risk and the main concern.
- "narrative": a short prose explanation (3-6 sentences) that ties the farm's evidence and the forecast to the
  recommended actions, written plainly for a smallholder farmer.
- "forecast_summary": one or two sentences describing the near-term outlook from the forecast evidence.
- "actions": a prioritised list of 3 to 5 actions (most important first). Each action is a task the farmer
  carries out as a short, ordered sequence of steps they can follow by hand:
  * "action": a short imperative title for the task (for example "Mulch the soil around the maize").
  * "steps": an ordered list of 2 to 4 short, specific steps that say exactly WHAT to do, HOW, and WHEN.
    Each step is one concrete instruction the farmer can act on (for example "Gather dry crop residue or
    grass from around the farm", then "Spread it about a hand's depth over the bare soil around the
    plants"). Prefer a concrete method and a rough quantity or timing, but never invent precise figures,
    products, or dates that are not supported by the evidence or passages.
  * "reason": one or two sentences explaining why this helps THIS farm, tied to its specific evidence
    (crop stage, irrigation type, current risk, forecast, or farmer notes).
  * "evidence": the evidence fields or passage facts the action rests on.
  Make the steps genuinely actionable; avoid vague verbs like "monitor", "consider", or "manage" as a
  step unless you spell out the concrete actions involved.
""".strip()

RECOMMENDATION_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "narrative", "forecast_summary", "actions"],
    "properties": {
        "summary": {"type": "string"},
        "narrative": {"type": "string"},
        "forecast_summary": {"type": "string"},
        "actions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["priority", "action", "steps", "reason", "evidence"],
                "properties": {
                    "priority": {"type": "integer", "minimum": 1, "maximum": 6},
                    "action": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 5,
                    },
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
