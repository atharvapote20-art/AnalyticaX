# Automated Data Analyst (AI Agent)

Beginner-friendly project to upload a dataset and automatically get:
- data profile + anomaly hints
- chart suggestions
- business insights/recommendations
- natural-language data Q&A

## Phase Plan

### Phase 1 - Local MVP (done in this starter)
- FastAPI backend
- Upload CSV/Excel
- Auto profiling (EDA summary, nulls, duplicates, outliers, correlations)
- Auto chart JSON generation (Plotly)
- Natural language endpoint (`/chat`)
- Beginner fallback mode when no API key is set

### Phase 2 - Stronger AI Analyst
- Add LangChain agent over SQL tool
- Better prompt templates for domain-specific recommendations
- Add follow-up memory per dataset/session
- Add insight confidence tags

### Phase 3 - Product UI
- Build simple frontend (Streamlit or React)
- Upload + profile + chart + chat in one dashboard
- Export report as PDF/Markdown

### Phase 4 - Production Readiness
- Persist metadata and chat history in a database
- Async job queue for large files
- Authentication + dataset access control
- Monitoring, logging, and tests in CI/CD

## Quick Start in VS Code (Windows)

1) Open terminal in project root:

```powershell
cd d:\Project\automated-data-analyst
```

2) Create and activate virtual environment (if needed):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3) Install dependencies:

```powershell
pip install -r requirements.txt
```

4) Optional: enable Gemini model
- Copy `.env.example` to `.env`
- Set `GEMINI_API_KEY=your_key`

Without key, the app still works in beginner fallback mode.

5) Run backend:

```powershell
uvicorn backend.main:app --reload --port 8000
```

6) Open API docs:
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## First Workflow

1) `POST /datasets/upload` with your CSV/Excel.
2) Call `POST /datasets/{dataset_id}/insights`.
3) Call `POST /datasets/{dataset_id}/charts`.
4) Call `POST /datasets/{dataset_id}/chat` with messages like:
   - `How many rows?`
   - `Show columns`
   - `What is the average of sales?`

## Current Backend Endpoints

- `GET /health`
- `POST /datasets/upload`
- `GET /datasets/{dataset_id}/profile`
- `POST /datasets/{dataset_id}/profile/rebuild`
- `POST /datasets/{dataset_id}/query`
- `POST /datasets/{dataset_id}/insights`
- `POST /datasets/{dataset_id}/charts`
- `POST /datasets/{dataset_id}/chat`

## Beginner Notes

- Start with one clean CSV (10k-100k rows).
- Keep column names simple (`sales`, `date`, `region`).
- Validate business meaning after every generated insight.
- Move to LangChain in Phase 2 once Phase 1 is stable.
