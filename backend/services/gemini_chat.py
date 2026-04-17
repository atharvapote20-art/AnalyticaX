from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.services import llm_client, rule_based_chat, warehouse


class SqlPlan(BaseModel):
    sql: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=800)
    confidence: int = Field(ge=0, le=100)


def _build_sql_plan(dataset_id: str, message: str) -> SqlPlan:
    schema = warehouse.table_schema_snippet(dataset_id)
    table = warehouse.table_name(dataset_id)
    prompt = f"""You convert natural language data questions into ONE safe DuckDB SQL query.
Return JSON only with keys: sql, explanation, confidence.
Constraints:
- SQL must start with SELECT
- no semicolons
- only table "{table}"
- quote table and columns with double-quotes
- add LIMIT 200 when listing rows
- for aggregations do not add unnecessary LIMIT
Schema:
{schema}
User question:
{message}
"""
    raw = llm_client.generate_json(prompt)
    return SqlPlan.model_validate(raw)


def _build_answer(message: str, plan: SqlPlan, result: dict[str, Any]) -> str:
    preview = json.dumps(result, default=str)[:18_000]
    prompt = f"""You are a data analyst assistant.
User question: {message}
Executed SQL: {plan.sql}
SQL explanation: {plan.explanation}
Query result JSON: {preview}
Write a concise answer in 2-4 lines. Mention if rows were truncated."""
    text = llm_client.generate_text(prompt)
    if text:
        return text
    return plan.explanation


def chat(dataset_id: str, message: str) -> dict[str, Any]:
    if not llm_client.is_enabled():
        return rule_based_chat.chat_without_llm(dataset_id, message)

    try:
        plan = _build_sql_plan(dataset_id, message)
        safe_sql = warehouse.validate_read_only_sql(plan.sql)
    except (ValueError, ValidationError, Exception):
        fallback = rule_based_chat.chat_without_llm(dataset_id, message)
        fallback["mode"] = "rule_based"
        return fallback

    try:
        result = warehouse.execute_read_only(dataset_id, safe_sql)
    except Exception as exc:
        return {
            "reply": f"I could not execute the generated SQL safely: {exc}",
            "generated_sql": safe_sql,
            "explanation": plan.explanation,
            "confidence": plan.confidence,
            "tool_trace": [{"query": safe_sql, "error": str(exc)}],
            "mode": "ai",
        }

    try:
        reply = _build_answer(message, plan, result)
    except Exception:
        reply = plan.explanation
    return {
        "reply": reply,
        "result": result,
        "generated_sql": safe_sql,
        "explanation": plan.explanation,
        "confidence": plan.confidence,
        "tool_trace": [{"query": safe_sql, "truncated": result.get("truncated")}],
        "mode": "ai",
    }
