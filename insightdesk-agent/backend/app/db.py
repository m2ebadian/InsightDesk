"""Small helper layer over SQLite. Every function opens its own connection, which keeps
things simple and is fine for the amount of traffic an internal tool like this gets."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence TEXT NOT NULL,
    top_score REAL NOT NULL,
    sources TEXT NOT NULL,
    feedback INTEGER,
    asked_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_passages_document ON passages(document_id);
"""


def now():
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


# ---------- documents ----------


def add_document(filename, file_type, size_bytes, chunks):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO documents (filename, file_type, size_bytes, uploaded_at) VALUES (?, ?, ?, ?)",
            (filename, file_type, size_bytes, now()),
        )
        doc_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO passages (document_id, position, text) VALUES (?, ?, ?)",
            [(doc_id, i, text) for i, text in enumerate(chunks, start=1)],
        )
    return get_document(doc_id)


def list_documents():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT d.*, COUNT(p.id) AS passage_count
            FROM documents d LEFT JOIN passages p ON p.document_id = d.id
            GROUP BY d.id
            ORDER BY d.uploaded_at DESC, d.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(doc_id):
    with connect() as conn:
        row = conn.execute(
            """
            SELECT d.*, COUNT(p.id) AS passage_count
            FROM documents d LEFT JOIN passages p ON p.document_id = d.id
            WHERE d.id = ?
            GROUP BY d.id
            """,
            (doc_id,),
        ).fetchone()
    return dict(row) if row else None


def get_document_passages(doc_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, position, text FROM passages WHERE document_id = ? ORDER BY position",
            (doc_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_document(doc_id):
    with connect() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return cur.rowcount > 0


def document_exists(filename):
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM documents WHERE filename = ?", (filename,)).fetchone()
    return row is not None


def all_passages():
    """Every passage plus the name of the file it came from, used to build the search index."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.document_id, p.position, p.text, d.filename
            FROM passages p JOIN documents d ON d.id = p.document_id
            ORDER BY p.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


# ---------- questions ----------


def save_question(question, answer, confidence, top_score, sources):
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO questions (question, answer, confidence, top_score, sources, asked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (question, answer, confidence, top_score, json.dumps(sources), now()),
        )
    return cur.lastrowid


def _question_row(row):
    item = dict(row)
    item["sources"] = json.loads(item["sources"])
    item["helpful"] = None if item["feedback"] is None else item["feedback"] == 1
    del item["feedback"]
    return item


def list_questions(limit=20):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_question_row(row) for row in rows]


def get_question(question_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    return _question_row(row) if row else None


def set_feedback(question_id, helpful):
    with connect() as conn:
        cur = conn.execute(
            "UPDATE questions SET feedback = ? WHERE id = ?",
            (1 if helpful else -1, question_id),
        )
    return cur.rowcount > 0


def question_stats():
    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(confidence = 'low') AS low_confidence,
                SUM(feedback = 1) AS helpful,
                SUM(feedback = -1) AS not_helpful
            FROM questions
            """
        ).fetchone()
        per_day = conn.execute(
            """
            SELECT substr(asked_at, 1, 10) AS day, COUNT(*) AS count
            FROM questions
            GROUP BY day ORDER BY day DESC LIMIT 14
            """
        ).fetchall()
        gaps = conn.execute(
            """
            SELECT id, question, top_score, asked_at FROM questions
            WHERE confidence = 'low' OR feedback = -1
            ORDER BY id DESC LIMIT 8
            """
        ).fetchall()
        sources = conn.execute("SELECT sources FROM questions").fetchall()

    return {
        "total": totals["total"],
        "low_confidence": totals["low_confidence"] or 0,
        "helpful": totals["helpful"] or 0,
        "not_helpful": totals["not_helpful"] or 0,
        "per_day": [dict(row) for row in reversed(per_day)],
        "gaps": [dict(row) for row in gaps],
        "source_lists": [json.loads(row["sources"]) for row in sources],
    }
