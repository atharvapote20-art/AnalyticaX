from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.services import warehouse


def _serialize_value(v: Any) -> Any:
    if isinstance(v, np.generic):
        return v.item()
    if pd.isna(v):
        return None
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return v


def build_dataset_preview(dataset_id: str, limit: int = 100) -> dict[str, Any]:
    conn = warehouse._connection()
    table = warehouse.ensure_dataset_registered(dataset_id)

    total_rows = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    df = conn.execute(f'SELECT * FROM "{table}" LIMIT {int(limit)}').df()

    columns: list[dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        entry: dict[str, Any] = {
            "name": col,
            "dtype": str(s.dtype),
            "null_pct": round(float(s.isna().mean()) if len(s) else 0.0, 4),
            "nunique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            entry["min"] = _serialize_value(s.min())
            entry["max"] = _serialize_value(s.max())
        elif pd.api.types.is_datetime64_any_dtype(s):
            entry["min"] = _serialize_value(s.min())
            entry["max"] = _serialize_value(s.max())
        else:
            vc = s.astype("string").value_counts(dropna=True).head(3)
            entry["top_values"] = {str(k): int(v) for k, v in vc.items()}
        columns.append(entry)

    preview_rows: list[list[Any]] = []
    for row in df.itertuples(index=False, name=None):
        preview_rows.append([_serialize_value(v) for v in row])

    return {
        "dataset_id": dataset_id,
        "table": table,
        "row_count_table": total_rows,
        "preview_row_count": len(preview_rows),
        "columns": columns,
        "column_names": list(df.columns),
        "rows": preview_rows,
        "truncated": total_rows > len(preview_rows),
    }
