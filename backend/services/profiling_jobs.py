from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.config import settings
from backend.services import warehouse


def _safe_float(x: Any) -> float | None:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _is_real_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def build_profile(dataset_id: str) -> dict[str, Any]:
    conn = warehouse._connection()
    t = warehouse.ensure_dataset_registered(dataset_id)
    n_total = int(conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
    df = conn.execute(
        f'SELECT * FROM "{t}" LIMIT {int(settings.profile_sample_rows)}'
    ).df()

    row_count_sample = len(df)
    columns: list[dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        dtype = str(s.dtype)
        null_pct = float(s.isna().mean()) if len(s) else 0.0
        nunique = int(s.nunique(dropna=True))
        entry: dict[str, Any] = {
            "name": col,
            "dtype": dtype,
            "null_pct": round(null_pct, 4),
            "nunique": nunique,
        }
        if _is_real_numeric(s):
            entry["min"] = _safe_float(s.min())
            entry["max"] = _safe_float(s.max())
            entry["mean"] = _safe_float(s.mean())
            entry["std"] = _safe_float(s.std())
            entry["median"] = _safe_float(s.median())
            entry["q1"] = _safe_float(s.quantile(0.25))
            entry["q3"] = _safe_float(s.quantile(0.75))
        elif pd.api.types.is_datetime64_any_dtype(s):
            entry["min"] = str(s.min()) if pd.notna(s.min()) else None
            entry["max"] = str(s.max()) if pd.notna(s.max()) else None
        else:
            vc = s.astype("string").value_counts(dropna=True).head(5)
            entry["top_values"] = {str(k): int(v) for k, v in vc.items()}
        columns.append(entry)

    anomalies: dict[str, Any] = {
        "duplicate_rows": int(df.duplicated().sum()) if len(df) else 0,
        "high_null_columns": [c["name"] for c in columns if c["null_pct"] > 0.5],
        "numeric_outliers": {},
    }

    numeric_cols = [c for c in df.columns if _is_real_numeric(df[c])]
    for col in numeric_cols[:30]:
        s = df[col].dropna()
        if len(s) < 10:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or not np.isfinite(iqr):
            continue
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (df[col] < low) | (df[col] > high)
        cnt = int(mask.sum())
        if cnt:
            anomalies["numeric_outliers"][col] = cnt

    correlations: list[dict[str, Any]] = []
    if len(numeric_cols) >= 2 and len(numeric_cols) <= 40:
        corr = df[numeric_cols].corr(numeric_only=True)
        pairs: list[tuple[float, str, str]] = []
        for i, a in enumerate(numeric_cols):
            for b in numeric_cols[i + 1 :]:
                v = corr.loc[a, b]
                if np.isfinite(v):
                    pairs.append((float(abs(v)), a, b))
        pairs.sort(reverse=True)
        for abs_v, a, b in pairs[:10]:
            v = float(corr.loc[a, b])
            correlations.append({"a": a, "b": b, "corr": round(v, 4)})

    time_col_candidate: str | None = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            time_col_candidate = col
            break
        if df[col].dtype == object:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.8:
                time_col_candidate = col
                break

    return {
        "dataset_id": dataset_id,
        "table": t,
        "row_count_table": n_total,
        "row_count_profile_sample": row_count_sample,
        "time_col_candidate": time_col_candidate,
        "columns": columns,
        "correlations": correlations,
        "anomalies": anomalies,
    }
