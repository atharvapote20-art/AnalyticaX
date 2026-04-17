import uuid
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.config import DATA_RAW, settings


ALLOWED = {".csv", ".xlsx", ".xls"}


def _safe_name(name: str) -> str:
    return Path(name).name.replace("..", "_")


def save_upload(file: UploadFile) -> tuple[str, Path, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type {suffix}. Use CSV or Excel.")

    dataset_id = str(uuid.uuid4())
    out_dir = DATA_RAW / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(_safe_name(file.filename)).stem
    ext = ".csv" if suffix == ".csv" else suffix
    dest = out_dir / f"{stem}{ext}"

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    try:
        with dest.open("wb") as f:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        out_dir.rmdir()
        raise

    if size == 0:
        dest.unlink(missing_ok=True)
        out_dir.rmdir()
        raise HTTPException(status_code=400, detail="Empty file")

    return dataset_id, dest, file.filename


def save_local_file_path(file_path: str) -> tuple[str, Path, str]:
    src = Path(file_path).expanduser()
    if not src.is_file():
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")

    suffix = src.suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type {suffix}. Use CSV or Excel.")

    dataset_id = str(uuid.uuid4())
    out_dir = DATA_RAW / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_name(src.name)
    dest = out_dir / safe_name
    shutil.copy2(src, dest)

    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        out_dir.rmdir()
        raise HTTPException(status_code=400, detail="Empty file")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if dest.stat().st_size > max_bytes:
        dest.unlink(missing_ok=True)
        out_dir.rmdir()
        raise HTTPException(status_code=413, detail="File too large")

    return dataset_id, dest, src.name
