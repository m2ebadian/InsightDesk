InsightDesk is a small internal-knowledge assistant that turns messy business notes, CSVs, and text files into a searchable Q&A tool with source snippets.

It is built to show practical AI/software skills without depending on a paid LLM API. The backend indexes documents locally with TF-IDF, retrieves the most relevant passages, and returns a grounded answer with citations. The frontend provides a clean chat-style interface and an upload/index workflow.

## Why I built it

A lot of teams have information spread across spreadsheets, notes, procedures, and project documents. InsightDesk is a lightweight way to search that information and get answers that point back to the original source instead of giving unsupported responses.

## Features

- Upload and index `.txt`, `.md`, and `.csv` files
- Ask natural-language questions over the indexed content
- Returns source snippets so answers can be checked
- Tracks “low confidence” responses instead of pretending to know
- Simple React dashboard with an API status panel
- FastAPI backend with clean endpoints and typed responses

## Tech Stack

**Backend:** Python, FastAPI, scikit-learn, pandas  
**Frontend:** React, TypeScript, Vite  
**Concepts shown:** document ingestion, retrieval, APIs, prompt/answer grounding, debugging, user-facing AI tools

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/health` | Checks API status |
| POST | `/index/sample` | Indexes sample documents |
| POST | `/ask` | Asks a question over indexed docs |

## Example Questions

After indexing sample docs, try:

- `What issues are slowing down the support process?`
- `Which process has the highest number of repeated errors?`
- `What should the team prioritize next?`

## Future Improvements

- Add PDF and Word document support
- Add authentication
- Store indexed documents in PostgreSQL
- Add optional OpenAI/Azure OpenAI answer generation
- Add feedback buttons to improve answer quality over time
