from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from .retriever import KnowledgeIndex

app = FastAPI(title="InsightDesk API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

index = KnowledgeIndex()

class AskRequest(BaseModel):
    question: str
    top_k: int = 3

@app.get("/health")
def health():
    return {"status": "ok", "indexed_passages": index.size}

@app.post("/index/sample")
def index_sample_docs():
    sample_path = Path(__file__).resolve().parents[2] / "sample_docs"
    count = index.load_folder(sample_path)
    return {"message": "Sample documents indexed", "passages": count}

@app.post("/ask")
def ask_question(request: AskRequest):
    if index.size == 0:
        raise HTTPException(status_code=400, detail="No documents indexed yet. Run /index/sample first.")

    result = index.ask(request.question, top_k=request.top_k)
    return result
