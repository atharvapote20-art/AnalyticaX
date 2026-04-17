# AnalyticaX

I built this project to practice full-stack development and data analysis workflows in one place.

With AnalyticaX, I can upload a CSV/Excel file, inspect the dataset, generate charts, and ask questions about the data in plain language.

## Features

- Upload dataset (`.csv`, `.xlsx`, `.xls`)
- Dataset preview and profile summary
- Insights and recommendations
- Custom chart builder
- Chat-based data questions
- PDF export
- Save and run chart dashboards

## Stack

- Frontend: React, TypeScript, Vite, Recharts
- Backend: FastAPI, Python, Pandas, DuckDB

## Run Locally (Windows)

```powershell
cd D:\Project\automated-data-analyst
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Open second terminal:

```powershell
cd D:\Project\automated-data-analyst\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open: `http://127.0.0.1:5173`

## Notes

- I keep `.env` private and never push it to GitHub.
- If model quota is unavailable, the chat switches to local rule-based responses.
