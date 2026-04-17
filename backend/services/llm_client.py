from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from backend.config import settings


def is_enabled() -> bool:
    return bool(settings.gemini_api_key)


def _model(response_json: bool) -> genai.GenerativeModel:
    genai.configure(api_key=settings.gemini_api_key)
    generation_config = genai.GenerationConfig(temperature=0.2)
    if response_json:
        generation_config.response_mime_type = "application/json"
    return genai.GenerativeModel(settings.gemini_model, generation_config=generation_config)


def generate_json(prompt: str) -> dict[str, Any]:
    model = _model(response_json=True)
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    if not text:
        raise ValueError("Empty LLM JSON response")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON returned by model") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON response must be an object")
    return parsed


def generate_text(prompt: str) -> str:
    model = _model(response_json=False)
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()
