from __future__ import annotations

import base64
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.services import warehouse


def _table_df_head(dataset_id: str, limit: int = 5000):
    conn = warehouse._connection()
    t = warehouse.ensure_dataset_registered(dataset_id)
    return conn.execute(f'SELECT * FROM "{t}" LIMIT {limit}').df()


def _to_plain(value: Any) -> Any:
    if isinstance(value, dict):
        if isinstance(value.get("dtype"), str) and isinstance(value.get("bdata"), str):
            decoded = _decode_plotly_binary(value["dtype"], value["bdata"])
            if decoded is not None:
                return decoded
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_to_plain(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _sort_for_x_axis(frame: pd.DataFrame, x_col: str) -> pd.DataFrame:
    if x_col not in frame.columns or frame.empty:
        return frame

    s = frame[x_col]
    if pd.api.types.is_numeric_dtype(s):
        return frame.sort_values(by=x_col, ascending=True)

    if pd.api.types.is_datetime64_any_dtype(s):
        return frame.sort_values(by=x_col, ascending=True)

    parsed_num = pd.to_numeric(s, errors="coerce")
    if parsed_num.notna().mean() >= 0.9:
        work = frame.copy()
        work[x_col] = parsed_num
        return work.sort_values(by=x_col, ascending=True)

    parsed_dt = pd.to_datetime(s, errors="coerce")
    if parsed_dt.notna().mean() >= 0.9:
        work = frame.copy()
        work[x_col] = parsed_dt
        return work.sort_values(by=x_col, ascending=True)

    return frame


def _apply_filters(df: pd.DataFrame, filters: list[dict[str, Any]] | None) -> pd.DataFrame:
    if not filters:
        return df
    out = df.copy()
    for item in filters:
        col = str(item.get("column") or "").strip()
        op = str(item.get("operator") or "=").strip().lower()
        raw = item.get("value")
        if not col or col not in out.columns:
            continue
        series = out[col]

        if op in ("=", "==", "eq"):
            out = out[series.astype(str).str.lower() == str(raw).lower()]
        elif op in ("!=", "<>", "ne"):
            out = out[series.astype(str).str.lower() != str(raw).lower()]
        elif op in ("contains",):
            out = out[series.astype(str).str.lower().str.contains(str(raw).lower(), na=False)]
        elif op in ("starts_with", "startswith"):
            out = out[series.astype(str).str.lower().str.startswith(str(raw).lower(), na=False)]
        elif op in ("ends_with", "endswith"):
            out = out[series.astype(str).str.lower().str.endswith(str(raw).lower(), na=False)]
        elif op in (">", ">=", "<", "<="):
            numeric_series = pd.to_numeric(series, errors="coerce")
            try:
                num = float(raw)
            except Exception:
                continue
            if op == ">":
                out = out[numeric_series > num]
            elif op == ">=":
                out = out[numeric_series >= num]
            elif op == "<":
                out = out[numeric_series < num]
            else:
                out = out[numeric_series <= num]
        if out.empty:
            break
    return out


def _decode_plotly_binary(dtype: str, bdata: str) -> list[Any] | None:
    dtype_map = {
        "i1": np.int8,
        "u1": np.uint8,
        "b1": np.uint8,
        "i2": np.int16,
        "u2": np.uint16,
        "i4": np.int32,
        "u4": np.uint32,
        "f4": np.float32,
        "f8": np.float64,
    }
    np_dtype = dtype_map.get(dtype)
    if np_dtype is None:
        return None
    try:
        raw = base64.b64decode(bdata)
        arr = np.frombuffer(raw, dtype=np_dtype)
        return arr.tolist()
    except Exception:
        return None


def build_charts(profile: dict[str, Any], dataset_id: str) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    df = _table_df_head(dataset_id, 8000)
    if df.empty:
        return charts

    time_col = profile.get("time_col_candidate")
    numeric_cols = [
        c["name"] for c in profile.get("columns", []) if str(c["dtype"]).startswith(("float", "int"))
    ]
    cat_cols = [
        c["name"]
        for c in profile.get("columns", [])
        if not str(c["dtype"]).startswith(("float", "int"))
        and c["nunique"] <= 25
        and c["nunique"] >= 2
    ]

    def add(title: str, fig) -> None:
        # Use plain python values to avoid Plotly binary encoding payloads (dtype/bdata).
        charts.append({"title": title, "plotly": _to_plain(fig.to_dict())})

    for col in numeric_cols[:4]:
        if col in df.columns:
            fig = px.histogram(df, x=col, nbins=40, title=f"Distribution: {col}")
            add(f"Histogram: {col}", fig)

    for col in cat_cols[:3]:
        if col in df.columns:
            vc = df[col].astype(str).value_counts().head(15).reset_index()
            vc.columns = ["category", "count"]
            fig = px.bar(vc, x="category", y="count", title=f"Top categories: {col}")
            add(f"Bar: {col}", fig)

    if time_col and time_col in df.columns and numeric_cols:
        tseries = df.copy()
        tseries[time_col] = pd.to_datetime(tseries[time_col], errors="coerce")
        tseries = tseries.dropna(subset=[time_col])
        num = numeric_cols[0]
        if num in tseries.columns:
            g = tseries.groupby(tseries[time_col].dt.floor("D"), as_index=False)[num].mean().dropna()
            if len(g) > 1:
                fig = px.line(g, x=time_col, y=num, title=f"{num} over time ({time_col})")
                add(f"Line: {num} by {time_col}", fig)

    corrs = profile.get("correlations") or []
    if corrs and numeric_cols:
        pair = corrs[0]
        a, b = pair.get("a"), pair.get("b")
        if a and b and a in df.columns and b in df.columns:
            sample = df[[a, b]].dropna()
            if len(sample) > 500:
                sample = sample.sample(500, random_state=0)
            fig = px.scatter(sample, x=a, y=b, title=f"Scatter: {a} vs {b}")
            add(f"Scatter: {a} vs {b}", fig)

    nums_for_heat = [
        c["name"] for c in profile.get("columns", []) if str(c["dtype"]).startswith(("float", "int"))
    ]
    nums_for_heat = [c for c in nums_for_heat if c in df.columns][:12]
    if len(nums_for_heat) >= 2:
        cmat = df[nums_for_heat].corr(numeric_only=True)
        fig = go.Figure(
            data=go.Heatmap(
                z=cmat.values,
                x=list(cmat.columns),
                y=list(cmat.index),
                colorscale="RdBu",
                zmid=0,
            )
        )
        fig.update_layout(title="Correlation heatmap (sample)")
        add("Correlation heatmap", fig)

    return charts[:10]


def build_custom_chart(
    dataset_id: str,
    chart_type: str,
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
    bins: int = 40,
    row_limit: int = 2000,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    safe_limit = max(100, min(int(row_limit), 20_000))
    df = _table_df_head(dataset_id, safe_limit)
    df = _apply_filters(df, filters)
    if df.empty:
        raise ValueError("No rows left after applying filters")

    t = chart_type.lower().strip()
    for col in [x, y, color]:
        if col and col not in df.columns:
            raise ValueError(f"Unknown column: {col}")

    def is_numeric(col: str | None) -> bool:
        return bool(col) and pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])

    def is_categorical(col: str | None) -> bool:
        if not col:
            return False
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            return False
        return True

    if t == "histogram":
        if not x:
            raise ValueError("Histogram requires x")
        if not is_numeric(x):
            raise ValueError("Histogram x must be numeric")
        series = df[[x]].dropna()
        if series.empty:
            raise ValueError("No data available for selected histogram column")
        edges = np.histogram_bin_edges(series[x].astype(float).values, bins=max(5, min(int(bins), 200)))
        counts, _ = np.histogram(series[x].astype(float).values, bins=edges)
        data = []
        for i, count in enumerate(counts):
            data.append(
                {
                    "bin_start": float(edges[i]),
                    "bin_end": float(edges[i + 1]),
                    "bin": f"{edges[i]:.2f} - {edges[i + 1]:.2f}",
                    "count": int(count),
                }
            )
        return {
            "chart_type": "histogram",
            "title": f"Histogram: {x}",
            "x_field": "bin",
            "y_field": "count",
            "data": data,
        }
    elif t == "bar":
        if not x:
            raise ValueError("Bar chart requires x")
        if y:
            if not is_numeric(y):
                raise ValueError("Bar chart y must be numeric")
            # Aggregate repeated category values into unique x categories.
            grouped = df[[x, y]].dropna().groupby(x, as_index=False)[y].mean()
            grouped = _sort_for_x_axis(grouped, x).head(60)
            data = grouped.to_dict(orient="records")
            return {
                "chart_type": "bar",
                "title": f"Bar: avg {y} by {x}",
                "x_field": x,
                "y_field": y,
                "data": _to_plain(data),
            }
        else:
            # Count by unique category.
            vc = df[x].astype(str).value_counts().head(30).reset_index()
            vc.columns = [x, "count"]
            vc = _sort_for_x_axis(vc, x)
            return {
                "chart_type": "bar",
                "title": f"Count by {x}",
                "x_field": x,
                "y_field": "count",
                "data": _to_plain(vc.to_dict(orient="records")),
            }
    elif t == "scatter":
        if not x or not y:
            raise ValueError("Scatter chart requires x and y")
        if not is_numeric(x) or not is_numeric(y):
            raise ValueError("Scatter x and y must both be numeric")
        sample = df[[x, y] + ([color] if color else [])].dropna()
        if len(sample) > 3000:
            sample = sample.sample(3000, random_state=7)
        sample = _sort_for_x_axis(sample, x)
        return {
            "chart_type": "scatter",
            "title": f"Scatter: {y} vs {x}",
            "x_field": x,
            "y_field": y,
            "color_field": color,
            "data": _to_plain(sample.to_dict(orient="records")),
        }
    elif t == "line":
        if not x or not y:
            raise ValueError("Line chart requires x and y")
        if not is_numeric(y):
            raise ValueError("Line chart y must be numeric")
        work = df[[x, y]].dropna()
        # Group on x to avoid repeated category labels in rendered data.
        grouped = work.groupby(x, as_index=False)[y].mean()
        grouped = _sort_for_x_axis(grouped, x)
        return {
            "chart_type": "line",
            "title": f"Line: avg {y} over {x}",
            "x_field": x,
            "y_field": y,
            "data": _to_plain(grouped.to_dict(orient="records")),
        }
    elif t == "heatmap":
        if not x or not y:
            raise ValueError("Heatmap requires x and y")
        if not is_numeric(x) or not is_numeric(y):
            raise ValueError("Heatmap x and y must both be numeric")
        work = df[[x, y]].dropna()
        if len(work) > 3000:
            work = work.sample(3000, random_state=7)
        work = _sort_for_x_axis(work, x)
        return {
            "chart_type": "scatter",
            "title": f"Heatmap proxy (scatter): {x} vs {y}",
            "x_field": x,
            "y_field": y,
            "data": _to_plain(work.to_dict(orient="records")),
            "note": "Rendered as scatter proxy in frontend.",
        }
    elif t == "box":
        if not y:
            raise ValueError("Box chart requires y")
        if not is_numeric(y):
            raise ValueError("Box chart y must be numeric")
        if x and not is_categorical(x):
            raise ValueError("Box chart x should be categorical (text/date)")
        if x:
            grouped = (
                df[[x, y]]
                .dropna()
                .groupby(x, as_index=False)[y]
                .agg(["min", "median", "mean", "max"])
                .reset_index()
            )
            grouped.columns = [x, "min", "median", "mean", "max"]
            return {
                "chart_type": "bar",
                "title": f"Box summary (mean by {x}) for {y}",
                "x_field": x,
                "y_field": "mean",
                "data": _to_plain(grouped.to_dict(orient="records")),
                "note": "Box summary shown as mean bar chart.",
            }
        summary = {
            "min": float(df[y].min()),
            "q1": float(df[y].quantile(0.25)),
            "median": float(df[y].median()),
            "mean": float(df[y].mean()),
            "q3": float(df[y].quantile(0.75)),
            "max": float(df[y].max()),
        }
        data = [{"metric": k, "value": v} for k, v in summary.items()]
        return {
            "chart_type": "bar",
            "title": f"Box summary stats for {y}",
            "x_field": "metric",
            "y_field": "value",
            "data": data,
            "note": "Box summary shown as metric bar chart.",
        }
    else:
        raise ValueError("Unsupported chart_type")
