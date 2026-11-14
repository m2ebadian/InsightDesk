from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)
    document_ids: list[int] | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("question can't be blank")
        return value


class Source(BaseModel):
    number: int
    document_id: int
    filename: str
    passage_id: int
    position: int
    score: float
    text: str


class Answer(BaseModel):
    id: int
    question: str
    answer: str
    confidence: str
    top_score: float
    sources: list[Source]
    asked_at: str
    helpful: bool | None = None


class Feedback(BaseModel):
    helpful: bool


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    size_bytes: int
    uploaded_at: str
    passage_count: int


class Passage(BaseModel):
    id: int
    position: int
    text: str


class DocumentDetail(DocumentOut):
    passages: list[Passage]


class UploadResult(BaseModel):
    uploaded: list[DocumentOut]
    errors: list[str]


class Health(BaseModel):
    status: str
    documents: int
    indexed_passages: int


class DayCount(BaseModel):
    day: str
    count: int


class Gap(BaseModel):
    id: int
    question: str
    top_score: float
    asked_at: str


class CitedDocument(BaseModel):
    filename: str
    citations: int


class Insights(BaseModel):
    total_questions: int
    low_confidence: int
    low_confidence_rate: float
    helpful: int
    not_helpful: int
    documents: int
    passages: int
    per_day: list[DayCount]
    knowledge_gaps: list[Gap]
    top_documents: list[CitedDocument]
