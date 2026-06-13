"""Prompt text and output schema for the recommendation engine.

Grounding context is no longer hardcoded here. It is retrieved at request time
from the local document corpus (see ``retrieval.py``) and passed to the model as
guidance passages. This module only owns the instruction text and the structured
output contract.
"""

PROMPT_VERSION = "recommendations.v5"

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
- "actions": a prioritised list of 3 to 5 concrete actions (most important first). Make every action
  descriptive and directly actionable for a smallholder farmer who will carry it out by hand:
  * "action": state exactly WHAT to do, HOW to do it, and WHEN/how often, in plain language. Prefer a
    specific method and a rough quantity or timing the farmer can act on (for example "spread a layer of
    crop-residue mulch about a hand's depth around the base of the plants" rather than "use mulch"), but
    never invent precise figures, products, or dates that are not supported by the evidence or passages.
  * "reason": one or two sentences explaining why this helps THIS farm, tied to its specific evidence
    (crop stage, irrigation type, current risk, forecast, or farmer notes).
  * "evidence": the evidence fields or passage facts the action rests on.
  Avoid vague verbs like "monitor", "consider", or "manage" unless you spell out the concrete steps.
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
