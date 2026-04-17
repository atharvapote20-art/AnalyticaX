import re
import threading
import uuid
from pathlib import Path

import duckdb
import pandas as pd

from backend.config import DATA_RAW, settings

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None


def _connection() -> duckdb.DuckDBPyConnection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = duckdb.connect(database=":memory:")
        return _conn


def table_name(dataset_id: str) -> str:
    safe = dataset_id.replace("-", "_").replace(".", "_")
    if not re.fullmatch(r"[0-9a-zA-Z_]+", safe):
        raise ValueError("Invalid dataset_id")
    return f"ds_{safe}"


def register_dataset(dataset_id: str, file_path: Path) -> str:
    conn = _connection()
    t = table_name(dataset_id)
    conn.execute(f'DROP TABLE IF EXISTS "{t}"')
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        fp = str(file_path.resolve()).replace("'", "''")
        conn.execute(
            f'CREATE TABLE "{t}" AS SELECT * FROM read_csv_auto(\'{fp}\', header=true, ignore_errors=true)'
        )
    else:
        df = pd.read_excel(file_path)
        tmp = f"_tmp_{uuid.uuid4().hex}"
        conn.register(tmp, df)
        conn.execute(f'CREATE TABLE "{t}" AS SELECT * FROM "{tmp}"')
        try:
            conn.unregister(tmp)
        except Exception:
            pass
    return t


def _validate_select(sql: str) -> str:
    q = sql.strip()
    if not q:
        raise ValueError("Empty query")
    if ";" in q:
        raise ValueError("Multiple statements are not allowed")
    if not re.match(r"(?is)^select\b", q):
        raise ValueError("Only SELECT queries are allowed")
    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|COPY|PRAGMA|CALL|GRANT|REVOKE)\b",
        re.IGNORECASE,
    )
    if forbidden.search(q):
        raise ValueError("Query contains forbidden keyword")
    return q


def validate_read_only_sql(sql: str) -> str:
    """Public validator for AI-generated SQL."""
    return _validate_select(sql)


def _table_exists(conn: duckdb.DuckDBPyConnection, t: str) -> bool:
    n = conn.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
        """,
        [t],
    ).fetchone()[0]
    return int(n) > 0


def _find_dataset_file(dataset_id: str) -> Path | None:
    folder = DATA_RAW / dataset_id
    if not folder.is_dir():
        return None
    for ext in (".csv", ".xlsx", ".xls"):
        matches = list(folder.glob(f"*{ext}"))
        if matches:
            return matches[0]
    files = [p for p in folder.iterdir() if p.is_file()]
    return files[0] if files else None


def ensure_dataset_registered(dataset_id: str) -> str:
    conn = _connection()
    t = table_name(dataset_id)
    if _table_exists(conn, t):
        return t
    src = _find_dataset_file(dataset_id)
    if not src:
        raise ValueError("Unknown dataset")
    register_dataset(dataset_id, src)
    return t


def execute_read_only(dataset_id: str, sql: str) -> dict:
    inner = _validate_select(sql)
    limit = settings.sql_max_rows
    wrapped = f'SELECT * FROM ({inner}) AS _sub LIMIT {limit + 1}'
    conn = _connection()
    t = ensure_dataset_registered(dataset_id)

    cur = conn.execute(wrapped)
    cols = [d[0] for d in cur.description]
    data = cur.fetchall()
    truncated = len(data) > limit
    if truncated:
        data = data[:limit]
    return {"columns": cols, "rows": [list(r) for r in data], "truncated": truncated}


def table_schema_snippet(dataset_id: str, max_cols: int = 80) -> str:
    conn = _connection()
    try:
        t = ensure_dataset_registered(dataset_id)
    except ValueError:
        return ""
    rows = conn.execute(f'DESCRIBE "{t}"').fetchall()
    lines = []
    for row in rows[:max_cols]:
        col = row[0]
        ctype = row[1]
        lines.append(f"- {col}: {ctype}")
    if len(rows) > max_cols:
        lines.append(f"... and {len(rows) - max_cols} more columns")
    return "\n".join(lines)
