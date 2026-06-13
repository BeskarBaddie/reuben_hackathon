RECOMMENDATION_SYSTEM_PROMPT = """
You write farmer-friendly adaptation recommendations from provided evidence only.
Return JSON only. Never invent measurements, risks, crops, locations, or dates.
If evidence is missing, return "insufficient data" for the affected field.
Do not calculate NDVI, climate anomalies, geospatial metrics, or risk scores.
""".strip()

PROMPT_VERSION = "recommendations.v1"

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
