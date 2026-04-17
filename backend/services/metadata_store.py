import json
from pathlib import Path
from typing import Any

from backend.config import DATA_META


def _path(dataset_id: str) -> Path:
    base = DATA_META / dataset_id
    base.mkdir(parents=True, exist_ok=True)
    return base / "profile.json"


def _latest_path() -> Path:
    DATA_META.mkdir(parents=True, exist_ok=True)
    return DATA_META / "latest_dataset_id.txt"


def _dashboards_path(dataset_id: str) -> Path:
    base = DATA_META / dataset_id
    base.mkdir(parents=True, exist_ok=True)
    return base / "dashboards.json"


def save_profile(dataset_id: str, profile: dict[str, Any]) -> None:
    p = _path(dataset_id)
    p.write_text(json.dumps(profile, indent=2, default=str), encoding="utf-8")
    _latest_path().write_text(dataset_id, encoding="utf-8")


def load_profile(dataset_id: str) -> dict[str, Any] | None:
    p = _path(dataset_id)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_latest_dataset_id() -> str | None:
    p = _latest_path()
    if not p.is_file():
        return None
    value = p.read_text(encoding="utf-8").strip()
    return value or None


def save_dashboards(dataset_id: str, dashboards: list[dict[str, Any]]) -> None:
    p = _dashboards_path(dataset_id)
    p.write_text(json.dumps(dashboards, indent=2, default=str), encoding="utf-8")


def load_dashboards(dataset_id: str) -> list[dict[str, Any]]:
    p = _dashboards_path(dataset_id)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []
