from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .parsing import ParseError, parse_file
from .retriever import KnowledgeIndex
from .schemas import (
    Answer,
    AskRequest,
    DocumentDetail,
    DocumentOut,
    Feedback,
    Health,
    Insights,
    UploadResult,
)

index = KnowledgeIndex()


def refresh_index():
    index.rebuild(db.all_passages())


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    refresh_index()
    yield


app = FastAPI(
    title="InsightDesk API",
    description="Ask questions over your team's notes, docs and spreadsheets and get answers with sources.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=Health)
def health():
    return {
        "status": "ok",
        "documents": len(db.list_documents()),
        "indexed_passages": index.size,
    }


# ---------- documents ----------


def add_file(filename, data):
    """Parses and stores one file. Raises ValueError with a readable message if it can't."""
    extension = Path(filename).suffix.lower()
    if extension not in config.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(config.ALLOWED_EXTENSIONS))
        raise ValueError(f"{filename}: unsupported file type (allowed: {allowed})")
    if not data:
        raise ValueError(f"{filename}: file is empty")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"{filename}: file is larger than {config.MAX_UPLOAD_MB} MB")

    try:
        passages = parse_file(filename, data)
    except ParseError as exc:
        raise ValueError(f"{filename}: {exc}") from exc

    return db.add_document(filename, extension.lstrip("."), len(data), passages)


@app.get("/documents", response_model=list[DocumentOut])
def list_documents():
    return db.list_documents()


@app.post("/documents", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
def upload_documents(files: list[UploadFile] = File(...)):
    uploaded = []
    errors = []
    for file in files:
        filename = Path(file.filename or "untitled.txt").name
        try:
            uploaded.append(add_file(filename, file.file.read()))
        except ValueError as exc:
            errors.append(str(exc))

    if not uploaded:
        raise HTTPException(status_code=400, detail=" ".join(errors) or "No files uploaded")

    refresh_index()
    return {"uploaded": uploaded, "errors": errors}


@app.post("/documents/sample", response_model=UploadResult)
def load_sample_documents():
    """Adds the files in sample_docs/ (skipping any that are already loaded)."""
    uploaded = []
    errors = []
    for path in sorted(config.SAMPLE_DOCS_DIR.glob("*")):
        if not path.is_file() or db.document_exists(path.name):
            continue
        try:
            uploaded.append(add_file(path.name, path.read_bytes()))
        except ValueError as exc:
            errors.append(str(exc))

    refresh_index()
    return {"uploaded": uploaded, "errors": errors}


@app.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int):
    document = db.get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {**document, "passages": db.get_document_passages(doc_id)}


@app.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int):
    if not db.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    refresh_index()


# ---------- questions ----------


@app.post("/ask", response_model=Answer)
def ask(request: AskRequest):
    if index.size == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Upload a file or load the sample documents.",
        )

    result = index.ask(request.question, request.top_k, request.document_ids)
    question_id = db.save_question(
        request.question,
        result["answer"],
        result["confidence"],
        result["top_score"],
        result["sources"],
    )
    return db.get_question(question_id)


@app.get("/questions", response_model=list[Answer])
def list_questions(limit: int = Query(20, ge=1, le=100)):
    return db.list_questions(limit)


@app.post("/questions/{question_id}/feedback", response_model=Answer)
def give_feedback(question_id: int, feedback: Feedback):
    if not db.set_feedback(question_id, feedback.helpful):
        raise HTTPException(status_code=404, detail="Question not found")
    return db.get_question(question_id)


@app.get("/insights", response_model=Insights)
def insights():
    stats = db.question_stats()

    citations = Counter()
    for sources in stats["source_lists"]:
        # count each document once per question, even if several of its passages were cited
        for filename in {s["filename"] for s in sources}:
            citations[filename] += 1

    total = stats["total"]
    return {
        "total_questions": total,
        "low_confidence": stats["low_confidence"],
        "low_confidence_rate": round(stats["low_confidence"] / total, 3) if total else 0.0,
        "helpful": stats["helpful"],
        "not_helpful": stats["not_helpful"],
        "documents": len(db.list_documents()),
        "passages": index.size,
        "per_day": stats["per_day"],
        "knowledge_gaps": stats["gaps"],
        "top_documents": [{"filename": f, "citations": c} for f, c in citations.most_common(6)],
    }
