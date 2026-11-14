from tests.conftest import upload

NOTES = (
    "Support Process Notes\n"
    "The largest slowdown is that employees have to search across multiple files to find the answer.\n"
    "Repeated errors happen when the same part number has different names in different systems.\n"
)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "documents": 0, "indexed_passages": 0}


def test_ask_before_indexing(client):
    response = client.post("/ask", json={"question": "anything?"})
    assert response.status_code == 400


def test_upload_list_and_delete(client):
    response = upload(client, "notes.txt", NOTES)
    assert response.status_code == 201
    doc = response.json()["uploaded"][0]
    assert doc["filename"] == "notes.txt"
    assert doc["file_type"] == "txt"
    assert doc["passage_count"] >= 1

    assert len(client.get("/documents").json()) == 1
    detail = client.get(f"/documents/{doc['id']}").json()
    assert "slowdown" in detail["passages"][0]["text"]
    assert client.get("/health").json()["indexed_passages"] == doc["passage_count"]

    assert client.delete(f"/documents/{doc['id']}").status_code == 204
    assert client.get("/documents").json() == []
    assert client.get("/health").json()["indexed_passages"] == 0
    assert client.delete(f"/documents/{doc['id']}").status_code == 404


def test_upload_rejects_bad_files(client):
    assert upload(client, "virus.exe", "MZ").status_code == 400
    assert upload(client, "empty.txt", "").status_code == 400


def test_upload_mixed_good_and_bad(client):
    response = client.post(
        "/documents",
        files=[
            ("files", ("good.md", b"# Title\nSome useful content about refunds.")),
            ("files", ("bad.exe", b"x")),
        ],
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["uploaded"]) == 1
    assert "unsupported file type" in body["errors"][0]


def test_upload_size_limit(client, monkeypatch):
    monkeypatch.setattr("app.config.MAX_UPLOAD_MB", 0)
    response = upload(client, "big.txt", NOTES)
    assert response.status_code == 400
    assert "larger than" in response.json()["detail"]


def test_ask_returns_answer_with_sources(client):
    upload(client, "notes.txt", NOTES)
    response = client.post("/ask", json={"question": "What is slowing down support?"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["sources"][0]["filename"] == "notes.txt"
    assert "search across multiple files" in body["answer"]
    assert body["helpful"] is None


def test_ask_validation(client):
    upload(client, "notes.txt", NOTES)
    assert client.post("/ask", json={"question": "   "}).status_code == 422
    assert client.post("/ask", json={"question": "hi", "top_k": 50}).status_code == 422


def test_history_and_feedback(client):
    upload(client, "notes.txt", NOTES)
    question_id = client.post("/ask", json={"question": "Why do repeated errors happen?"}).json()["id"]
    client.post("/ask", json={"question": "What is the parking policy?"})

    history = client.get("/questions").json()
    assert [q["question"] for q in history] == [
        "What is the parking policy?",
        "Why do repeated errors happen?",
    ]

    response = client.post(f"/questions/{question_id}/feedback", json={"helpful": True})
    assert response.json()["helpful"] is True
    assert client.post("/questions/999/feedback", json={"helpful": True}).status_code == 404


def test_insights(client):
    upload(client, "notes.txt", NOTES)
    good = client.post("/ask", json={"question": "Why do repeated errors happen?"}).json()
    client.post("/ask", json={"question": "What is the parking policy?"})
    client.post(f"/questions/{good['id']}/feedback", json={"helpful": False})

    data = client.get("/insights").json()
    assert data["total_questions"] == 2
    assert data["low_confidence"] == 1
    assert data["low_confidence_rate"] == 0.5
    assert data["not_helpful"] == 1
    assert data["documents"] == 1
    assert data["per_day"][0]["count"] == 2
    # both the unanswered question and the one marked not helpful count as gaps
    assert len(data["knowledge_gaps"]) == 2
    assert data["top_documents"] == [{"filename": "notes.txt", "citations": 1}]


def test_sample_documents(client):
    first = client.post("/documents/sample").json()
    assert len(first["uploaded"]) >= 5
    assert first["errors"] == []
    # running it again doesn't add duplicates
    assert client.post("/documents/sample").json()["uploaded"] == []

    answer = client.post(
        "/ask", json={"question": "Which process has the highest number of repeated errors?"}
    ).json()
    assert "Replacement part search" in answer["answer"]
