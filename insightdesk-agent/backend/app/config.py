import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# Where the SQLite database lives. Docker mounts a volume here so data survives restarts.
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "insightdesk.db"

SAMPLE_DOCS_DIR = Path(os.getenv("SAMPLE_DOCS_DIR", BASE_DIR.parent / "sample_docs"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx"}

# Only needed if the frontend is served from a different origin than the API.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
