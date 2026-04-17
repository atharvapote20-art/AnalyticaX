import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.services import llm_client, rule_based_insights


class InsightModel(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    category: str
    severity: str
    confidence: int = Field(ge=0, le=100)
    why: str = Field(min_length=1, max_length=1000)
    action: str = Field(min_length=1, max_length=1000)


class InsightsPayload(BaseModel):
    insights: list[InsightModel] = Field(default_factory=list, max_length=8)
    data_quality_risks: list[InsightModel] = Field(default_factory=list, max_length=6)
    recommendations: list[InsightModel] = Field(default_factory=list, max_length=8)


def _normalize_items(items: Any, category: str, default_severity: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in list(items or []):
        if isinstance(raw, str):
            out.append(
                {
                    "message": raw[:500],
                    "category": category,
                    "severity": default_severity,
                    "confidence": 75,
                    "why": "Generated from profile-based analysis.",
                    "action": "Validate and prioritize this item in the next review.",
                }
            )
            continue
        if isinstance(raw, dict):
            out.append(
                {
                    "message": str(raw.get("message") or raw.get("insight") or "")[:500],
                    "category": str(raw.get("category") or category),
                    "severity": str(raw.get("severity") or default_severity).lower(),
                    "confidence": int(raw.get("confidence") or 70),
                    "why": str(raw.get("why") or "Derived from detected patterns."),
                    "action": str(raw.get("action") or "Review and operationalize if relevant."),
                }
            )
    return out


def generate_insights(profile: dict) -> dict:
    if not llm_client.is_enabled():
        return rule_based_insights.generate_from_profile(profile)

    payload = json.dumps(profile, default=str)[:120_000]
    prompt = f"""You are a senior data analyst. Use ONLY the JSON profile below.
If a fact is not present, say you cannot infer it. Do not invent column names or numbers.
Return JSON with keys:
- insights: array(max 8) of objects {{message, category='insight', severity(high|medium|low), confidence(0-100), why, action}}
- data_quality_risks: array(max 6) of objects {{message, category='risk', severity(high|medium|low), confidence(0-100), why, action}}
- recommendations: array(max 8) of objects {{message, category='recommendation', severity(high|medium|low), confidence(0-100), why, action}}

PROFILE_JSON:
{payload}
"""
    try:
        raw = llm_client.generate_json(prompt)
        parsed = InsightsPayload.model_validate(raw)
    except (ValueError, ValidationError, Exception):
        # Keep response strict and always schema-compliant via deterministic fallback.
        return rule_based_insights.generate_from_profile(profile)

    return {
        "insights": _normalize_items(
            [item.model_dump() for item in parsed.insights],
            "insight",
            "medium",
        ),
        "data_quality_risks": _normalize_items(
            [item.model_dump() for item in parsed.data_quality_risks],
            "risk",
            "high",
        ),
        "recommendations": _normalize_items(
            [item.model_dump() for item in parsed.recommendations],
            "recommendation",
            "medium",
        ),
    }
