from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from backend.config import DATA_META, DATA_RAW, settings
from backend.services import (
    chart_suggestions,
    dataset_preview,
    gemini_chat,
    gemini_insights,
    ingestion,
    metadata_store,
    profiling_jobs,
    warehouse,
)

app = FastAPI(title="Automated Data Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_dataset_id() -> str:
    latest = metadata_store.load_latest_dataset_id()
    if not latest:
        raise HTTPException(status_code=404, detail="No uploaded dataset found. Upload a dataset first.")
    return latest


@app.on_event("startup")
def _ensure_data_dirs() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_META.mkdir(parents=True, exist_ok=True)


class SqlBody(BaseModel):
    sql: str


class LocalPathUploadBody(BaseModel):
    path: str


class ChatBody(BaseModel):
    message: str


class CustomChartBody(BaseModel):
    chart_type: str
    x: str | None = None
    y: str | None = None
    color: str | None = None
    bins: int = 40
    row_limit: int = 2000
    filters: list[dict] = []


class DashboardBody(CustomChartBody):
    name: str


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    try:
        dataset_id, dest, orig = ingestion.save_upload(file)
        warehouse.register_dataset(dataset_id, dest)
        profile = profiling_jobs.build_profile(dataset_id)
        metadata_store.save_profile(dataset_id, profile)
        return {"dataset_id": dataset_id, "filename": orig, "profile": profile}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {e}") from e


@app.post("/datasets/upload-by-path")
def upload_dataset_by_path(body: LocalPathUploadBody) -> dict:
    try:
        dataset_id, dest, orig = ingestion.save_local_file_path(body.path)
        warehouse.register_dataset(dataset_id, dest)
        profile = profiling_jobs.build_profile(dataset_id)
        metadata_store.save_profile(dataset_id, profile)
        return {"dataset_id": dataset_id, "filename": orig, "profile": profile}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload by path failed: {e}") from e


@app.get("/datasets/profile")
def get_profile() -> dict:
    dataset_id = _resolve_dataset_id()
    p = metadata_store.load_profile(dataset_id)
    if not p:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return p


@app.post("/datasets/profile/rebuild")
def rebuild_profile() -> dict:
    dataset_id = _resolve_dataset_id()
    try:
        profile = profiling_jobs.build_profile(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    metadata_store.save_profile(dataset_id, profile)
    return profile


@app.post("/datasets/query")
def run_query(body: SqlBody) -> dict:
    dataset_id = _resolve_dataset_id()
    try:
        return warehouse.execute_read_only(dataset_id, body.sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/datasets/insights")
def insights() -> dict:
    dataset_id = _resolve_dataset_id()
    p = metadata_store.load_profile(dataset_id)
    if not p:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return gemini_insights.generate_insights(p)


@app.post("/datasets/charts")
def charts() -> dict:
    dataset_id = _resolve_dataset_id()
    p = metadata_store.load_profile(dataset_id)
    if not p:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return {"charts": chart_suggestions.build_charts(p, dataset_id)}


@app.post("/datasets/charts/custom")
def custom_chart(body: CustomChartBody) -> dict:
    dataset_id = _resolve_dataset_id()
    try:
        chart = chart_suggestions.build_custom_chart(
            dataset_id=dataset_id,
            chart_type=body.chart_type,
            x=body.x,
            y=body.y,
            color=body.color,
            bins=body.bins,
            row_limit=body.row_limit,
            filters=body.filters,
        )
        return {"charts": [chart]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/datasets/chat")
def chat(body: ChatBody) -> dict:
    dataset_id = _resolve_dataset_id()
    return gemini_chat.chat(dataset_id, body.message)


@app.get("/datasets/dashboards")
def list_dashboards() -> dict:
    dataset_id = _resolve_dataset_id()
    return {"dashboards": metadata_store.load_dashboards(dataset_id)}


@app.post("/datasets/dashboards")
def save_dashboard(body: DashboardBody) -> dict:
    dataset_id = _resolve_dataset_id()
    existing = metadata_store.load_dashboards(dataset_id)
    item = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip() or "Untitled Dashboard",
        "config": {
            "chart_type": body.chart_type,
            "x": body.x,
            "y": body.y,
            "color": body.color,
            "bins": body.bins,
            "row_limit": body.row_limit,
            "filters": body.filters,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    existing.append(item)
    metadata_store.save_dashboards(dataset_id, existing)
    return {"saved": item, "dashboards": existing}


@app.delete("/datasets/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str) -> dict:
    dataset_id = _resolve_dataset_id()
    existing = metadata_store.load_dashboards(dataset_id)
    next_items = [d for d in existing if str(d.get("id")) != dashboard_id]
    metadata_store.save_dashboards(dataset_id, next_items)
    return {"dashboards": next_items}


@app.post("/datasets/dashboards/{dashboard_id}/run")
def run_dashboard(dashboard_id: str) -> dict:
    dataset_id = _resolve_dataset_id()
    dashboards = metadata_store.load_dashboards(dataset_id)
    selected = next((d for d in dashboards if str(d.get("id")) == dashboard_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    config = selected.get("config") or {}
    try:
        chart = chart_suggestions.build_custom_chart(
            dataset_id=dataset_id,
            chart_type=str(config.get("chart_type") or ""),
            x=config.get("x"),
            y=config.get("y"),
            color=config.get("color"),
            bins=int(config.get("bins") or 40),
            row_limit=int(config.get("row_limit") or 2000),
            filters=list(config.get("filters") or []),
        )
        return {"charts": [chart], "dashboard": selected}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/datasets/dataset")
def dataset() -> dict:
    dataset_id = _resolve_dataset_id()
    try:
        return dataset_preview.build_dataset_preview(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dataset preview failed: {e}") from e
