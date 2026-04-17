from __future__ import annotations

import re

from backend.services import warehouse


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _match_column(dataset_id: str, message: str) -> str | None:
    normalized_msg = _normalize(message)
    columns = sorted(_columns(dataset_id), key=len, reverse=True)
    for col in columns:
        phrase = _normalize(col)
        if not phrase:
            continue
        if re.search(rf"(^|\s){re.escape(phrase)}(\s|$)", normalized_msg):
            return col
    return None


def _columns(dataset_id: str) -> list[str]:
    conn = warehouse._connection()
    table = warehouse.table_name(dataset_id)
    rows = conn.execute(f'DESCRIBE "{table}"').fetchall()
    return [str(r[0]) for r in rows]


def _try_avg_for_mentioned_column(dataset_id: str, message: str) -> dict | None:
    msg = message.lower()
    if "average" not in msg and "mean" not in msg and "avg" not in msg:
        return None
    matched_col = _match_column(dataset_id, message)
    if matched_col:
        sql = f'SELECT AVG("{matched_col}") AS average_{matched_col} FROM "{warehouse.table_name(dataset_id)}"'
        result = warehouse.execute_read_only(dataset_id, sql)
        return {
            "reply": f'Calculated average for "{matched_col}".',
            "tool_trace": [{"query": sql}],
            "generated_sql": sql,
            "explanation": f'Computed the average of "{matched_col}" from your dataset.',
            "confidence": 95,
            "result": result,
            "mode": "rule_based",
        }
    return None


def _try_count_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    if "count" not in msg and "number of" not in msg:
        return None

    table = warehouse.table_name(dataset_id)
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None

    # Count grouped by a column (useful for prompts like "count people in gender column").
    if any(token in msg for token in ("each", "per", "group", "specific column", "in column", "by")):
        sql = (
            f'SELECT "{matched_col}" AS category, COUNT(*) AS total_count '
            f'FROM "{table}" GROUP BY 1 ORDER BY total_count DESC LIMIT 200'
        )
        result = warehouse.execute_read_only(dataset_id, sql)
        return {
            "reply": f'Counted records grouped by "{matched_col}".',
            "tool_trace": [{"query": sql}],
            "generated_sql": sql,
            "explanation": f'Grouped all rows by "{matched_col}" and counted records in each category.',
            "confidence": 92,
            "result": result,
            "mode": "rule_based",
        }

    # Count rows where the mentioned column is not null.
    sql = f'SELECT COUNT("{matched_col}") AS non_null_count FROM "{table}"'
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Counted non-empty values in "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Computed how many rows contain a value in "{matched_col}".',
        "confidence": 90,
        "result": result,
        "mode": "rule_based",
    }


def _extract_filter_value(message: str, column: str) -> str | None:
    col = re.escape(column.lower())
    m = re.search(rf'{col}\s*(?:=|is|equals)\s*["\']?([a-z0-9 _\-.]+?)["\']?(?:\s|$)', message.lower())
    if not m:
        return None
    value = (m.group(1) or "").strip()
    return value or None


def _try_value_filtered_count(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    if ("count" not in msg and "how many" not in msg and "number of" not in msg) or "where" not in msg:
        return None
    col = _match_column(dataset_id, message)
    if not col:
        return None
    value = _extract_filter_value(message, col)
    if not value:
        return None
    table = warehouse.table_name(dataset_id)
    safe_val = value.replace("'", "''")
    sql = (
        f'SELECT COUNT(*) AS filtered_count FROM "{table}" '
        f'WHERE LOWER(CAST("{col}" AS VARCHAR)) = LOWER(\'{safe_val}\')'
    )
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Counted rows where "{col}" is "{value}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Matched rows filtered by {col} = {value} and returned the count.',
        "confidence": 90,
        "result": result,
        "mode": "rule_based",
    }


def _try_unique_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    if "unique" not in msg and "distinct" not in msg:
        return None
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None
    table = warehouse.table_name(dataset_id)
    sql = f'SELECT COUNT(DISTINCT "{matched_col}") AS distinct_count FROM "{table}"'
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Computed unique value count for "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Calculated the number of distinct values in "{matched_col}".',
        "confidence": 92,
        "result": result,
        "mode": "rule_based",
    }


def _try_min_max_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    wants_min = "minimum" in msg or re.search(r"\bmin\b", msg) is not None
    wants_max = "maximum" in msg or re.search(r"\bmax\b", msg) is not None
    if not wants_min and not wants_max:
        return None
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None
    table = warehouse.table_name(dataset_id)
    select_parts: list[str] = []
    if wants_min:
        select_parts.append(f'MIN("{matched_col}") AS min_value')
    if wants_max:
        select_parts.append(f'MAX("{matched_col}") AS max_value')
    sql = f'SELECT {", ".join(select_parts)} FROM "{table}"'
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Computed {" and ".join(["minimum" if wants_min else "", "maximum" if wants_max else ""]).strip(" and")} for "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Returned the requested range statistic(s) for "{matched_col}".',
        "confidence": 90,
        "result": result,
        "mode": "rule_based",
    }


def _try_sum_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    if "sum" not in msg and "total" not in msg:
        return None
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None
    table = warehouse.table_name(dataset_id)
    sql = f'SELECT SUM("{matched_col}") AS total_sum FROM "{table}"'
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Computed total sum for "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Added all values from "{matched_col}".',
        "confidence": 90,
        "result": result,
        "mode": "rule_based",
    }


def _try_null_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    if "null" not in msg and "missing" not in msg and "empty" not in msg:
        return None
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None
    table = warehouse.table_name(dataset_id)
    sql = (
        f'SELECT COUNT(*) FILTER (WHERE "{matched_col}" IS NULL) AS null_count, '
        f'COUNT(*) AS total_rows FROM "{table}"'
    )
    result = warehouse.execute_read_only(dataset_id, sql)
    return {
        "reply": f'Counted missing values for "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Computed null count and total rows for "{matched_col}".',
        "confidence": 92,
        "result": result,
        "mode": "rule_based",
    }


def _try_top_bottom_requests(dataset_id: str, message: str) -> dict | None:
    msg = message.lower().strip()
    is_top = "top" in msg or "highest" in msg
    is_bottom = "bottom" in msg or "lowest" in msg
    if not is_top and not is_bottom:
        return None
    matched_col = _match_column(dataset_id, message)
    if not matched_col:
        return None
    n_match = re.search(r"\b(\d{1,3})\b", msg)
    n = int(n_match.group(1)) if n_match else 10
    n = max(1, min(n, 100))
    table = warehouse.table_name(dataset_id)
    direction = "DESC" if is_top else "ASC"
    sql = f'SELECT "{matched_col}" FROM "{table}" ORDER BY "{matched_col}" {direction} LIMIT {n}'
    result = warehouse.execute_read_only(dataset_id, sql)
    label = "top" if is_top else "bottom"
    return {
        "reply": f'Retrieved {label} {n} values from "{matched_col}".',
        "tool_trace": [{"query": sql}],
        "generated_sql": sql,
        "explanation": f'Ranked "{matched_col}" and returned {label} {n} rows.',
        "confidence": 88,
        "result": result,
        "mode": "rule_based",
    }


def chat_without_llm(dataset_id: str, message: str) -> dict:
    msg = message.lower().strip()
    table = warehouse.table_name(dataset_id)

    if "how many rows" in msg or ("row" in msg and "count" in msg):
        sql = f'SELECT COUNT(*) AS total_rows FROM "{table}"'
        result = warehouse.execute_read_only(dataset_id, sql)
        return {
            "reply": "Here is the row count.",
            "tool_trace": [{"query": sql}],
            "generated_sql": sql,
            "explanation": "Counted rows directly from the active dataset table.",
            "confidence": 95,
            "result": result,
            "mode": "rule_based",
        }

    if "columns" in msg or "schema" in msg:
        cols = _columns(dataset_id)
        return {
            "reply": "These are the available columns: " + ", ".join(cols[:50]),
            "tool_trace": [],
            "generated_sql": "",
            "explanation": "Read schema metadata from the active dataset table.",
            "confidence": 90,
            "mode": "rule_based",
        }

    avg_result = _try_avg_for_mentioned_column(dataset_id, message)
    if avg_result:
        return avg_result
    filtered_count = _try_value_filtered_count(dataset_id, message)
    if filtered_count:
        return filtered_count
    count_result = _try_count_requests(dataset_id, message)
    if count_result:
        return count_result
    unique_result = _try_unique_requests(dataset_id, message)
    if unique_result:
        return unique_result
    min_max_result = _try_min_max_requests(dataset_id, message)
    if min_max_result:
        return min_max_result
    sum_result = _try_sum_requests(dataset_id, message)
    if sum_result:
        return sum_result
    null_result = _try_null_requests(dataset_id, message)
    if null_result:
        return null_result
    top_bottom_result = _try_top_bottom_requests(dataset_id, message)
    if top_bottom_result:
        return top_bottom_result

    return {
        "reply": (
            "I could not map that request yet in local analysis mode. "
            "Try one of these: row count, columns/schema, average, sum/total, min/max, "
            "unique/distinct count, missing/null count, top/bottom N, or grouped counts by a column."
        ),
        "tool_trace": [],
        "generated_sql": "",
        "explanation": "Request not matched to a supported local intent.",
        "confidence": 60,
        "mode": "rule_based",
    }
