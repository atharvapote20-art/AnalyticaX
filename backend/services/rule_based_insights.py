from __future__ import annotations

from typing import Any


def _item(
    *,
    message: str,
    category: str,
    severity: str,
    confidence: int,
    why: str,
    action: str,
) -> dict[str, Any]:
    return {
        "message": message,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "why": why,
        "action": action,
    }


def generate_from_profile(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    columns = profile.get("columns") or []
    row_count = int(profile.get("row_count_table") or 0)
    anomalies = profile.get("anomalies") or {}
    correlations = profile.get("correlations") or []

    insights: list[dict[str, Any]] = []
    data_quality_risks: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    if row_count:
        insights.append(
            _item(
                message=f"Dataset has about {row_count:,} rows.",
                category="insight",
                severity="low",
                confidence=95,
                why="Row count indicates dataset size and model feasibility.",
                action="Use row sampling for fast iteration and full-data runs for final reporting.",
            )
        )
    insights.append(
        _item(
            message=f"Dataset has {len(columns)} columns.",
            category="insight",
            severity="low",
            confidence=95,
            why="Column count suggests feature breadth and complexity.",
            action="Prioritize the most business-relevant columns for first dashboards.",
        )
    )

    numeric_cols = [c for c in columns if str(c.get("dtype", "")).startswith(("float", "int"))]
    cat_cols = [c for c in columns if c not in numeric_cols]
    if numeric_cols:
        insights.append(
            _item(
                message=f"Detected {len(numeric_cols)} numeric columns for trend and anomaly analysis.",
                category="insight",
                severity="medium",
                confidence=90,
                why="Numeric fields are required for KPI trends and outlier checks.",
                action="Create baseline metric charts for each key numeric column.",
            )
        )
    if cat_cols:
        insights.append(
            _item(
                message=f"Detected {len(cat_cols)} non-numeric columns for segmentation.",
                category="insight",
                severity="medium",
                confidence=88,
                why="Categorical features enable cohort and segment analysis.",
                action="Build segmented views by top categories and compare performance.",
            )
        )

    high_null_columns = anomalies.get("high_null_columns") or []
    if high_null_columns:
        data_quality_risks.append(
            _item(
                message="High missing values in: " + ", ".join(high_null_columns[:6]),
                category="risk",
                severity="high",
                confidence=92,
                why="Missingness can bias metrics and lead to unreliable conclusions.",
                action="Impute or exclude these columns after domain review.",
            )
        )

    duplicate_rows = int(anomalies.get("duplicate_rows") or 0)
    if duplicate_rows > 0:
        data_quality_risks.append(
            _item(
                message=f"Found around {duplicate_rows:,} duplicate rows in sampled data.",
                category="risk",
                severity="medium",
                confidence=85,
                why="Duplicates can inflate counts and distort aggregate statistics.",
                action="Define deduplication keys and remove duplicate records before reporting.",
            )
        )

    numeric_outliers = anomalies.get("numeric_outliers") or {}
    if numeric_outliers:
        top_outliers = sorted(numeric_outliers.items(), key=lambda x: x[1], reverse=True)[:5]
        outlier_text = ", ".join(f"{name} ({count})" for name, count in top_outliers)
        data_quality_risks.append(
            _item(
                message=f"Possible outliers detected in: {outlier_text}.",
                category="risk",
                severity="medium",
                confidence=80,
                why="Extreme values may indicate data issues or rare but important behavior.",
                action="Review outlier rows with business owners before any filtering.",
            )
        )

    if correlations:
        best = correlations[0]
        insights.append(
            _item(
                message=(
                    f"Strong relationship observed between {best.get('a')} and {best.get('b')} "
                    f"(corr {best.get('corr')})."
                ),
                category="insight",
                severity="medium",
                confidence=86,
                why="Correlation hints which drivers may influence outcomes together.",
                action="Investigate causality before using correlation for decisions.",
            )
        )

    recommendations.append(
        _item(
            message="Validate missing-value strategy (drop, impute, or business defaults).",
            category="recommendation",
            severity="high",
            confidence=90,
            why="Handling nulls early improves all downstream analysis quality.",
            action="Finalize a documented missing-data policy per column group.",
        )
    )
    recommendations.append(
        _item(
            message="Create a KPI dashboard with 3-5 key metrics relevant to stakeholders.",
            category="recommendation",
            severity="medium",
            confidence=88,
            why="Focused KPI views improve decision-making speed.",
            action="Publish a weekly dashboard with trend and segment breakdown.",
        )
    )
    if profile.get("time_col_candidate"):
        recommendations.append(
            _item(
                message="Add a time-trend chart to monitor performance over days/weeks.",
                category="recommendation",
                severity="medium",
                confidence=85,
                why="Time-based monitoring helps detect seasonality and shifts quickly.",
                action="Track moving average and week-over-week change for core KPIs.",
            )
        )
    if numeric_outliers:
        recommendations.append(
            _item(
                message="Review outlier records with domain team before removing them.",
                category="recommendation",
                severity="medium",
                confidence=83,
                why="Some outliers are true business signals, not noise.",
                action="Create an outlier-review checklist and annotate decisions.",
            )
        )

    return {
        "insights": insights[:8],
        "data_quality_risks": data_quality_risks[:6],
        "recommendations": recommendations[:8],
    }
