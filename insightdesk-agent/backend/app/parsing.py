"""Turns uploaded files into a list of text passages that can be searched."""

import csv
import io
import re

from docx import Document
from pypdf import PdfReader

MAX_WORDS_PER_PASSAGE = 100


class ParseError(Exception):
    pass


def split_sentences(text):
    """Very simple sentence splitter: breaks on line breaks and on . ! ? followed by a space."""
    sentences = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            if part.strip():
                sentences.append(part.strip())
    return sentences


def chunk_text(text, max_words=MAX_WORDS_PER_PASSAGE):
    """Groups whole sentences into passages of roughly `max_words` words.

    The last sentence of each passage is repeated at the start of the next one so an
    answer that sits right on the boundary doesn't get cut in half. Sentences are joined
    with newlines so they can be split apart again later when building an answer.
    """
    sentences = split_sentences(text)
    chunks = []
    current = []
    word_count = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current and word_count + words > max_words:
            chunks.append("\n".join(current))
            current = [current[-1]]
            word_count = len(current[0].split())
        current.append(sentence)
        word_count += words

    if current:
        chunks.append("\n".join(current))

    # drop tiny fragments like a lone page number
    return [chunk for chunk in chunks if len(chunk) > 20]


def clean_markdown(text):
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^#+\s*", "", line)  # headings
        line = re.sub(r"^\s*[-*]\s+", "", line)  # bullet points
        line = line.replace("**", "").replace("`", "")
        lines.append(line)
    return "\n".join(lines)


def pretty(column):
    return column.replace("_", " ").strip()


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_number(value):
    return str(int(value)) if value == int(value) else f"{value:g}"


def csv_passages(text):
    """One passage per row, plus a summary passage for each numeric column.

    The summaries are what let questions like "which process has the most errors?"
    find an answer, since that information isn't written in any single row.
    """
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader if any((v or "").strip() for v in row.values())]
    if not reader.fieldnames or not rows:
        return []

    columns = [c for c in reader.fieldnames if c]
    numeric = [c for c in columns if all(to_number(row.get(c)) is not None for row in rows)]
    label_column = next((c for c in columns if c not in numeric), columns[0])

    passages = []
    for row in rows:
        details = "; ".join(f"{pretty(c)}: {(row.get(c) or '').strip()}" for c in columns)
        passages.append(f"{details}.")

    for column in numeric:
        values = [(to_number(row[column]), row[label_column]) for row in rows]
        high = max(values)
        low = min(values)
        average = sum(v for v, _ in values) / len(values)
        passages.append(
            f"The highest {pretty(column)} is {high[1]} with {format_number(high[0])}.\n"
            f"The lowest {pretty(column)} is {low[1]} with {format_number(low[0])}.\n"
            f"The average {pretty(column)} across all {pretty(label_column)} rows is {average:.1f}."
        )
    return passages


def pdf_text(data):
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ParseError("Couldn't read this PDF. It may be encrypted or damaged.") from exc


def docx_text(data):
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise ParseError("Couldn't read this Word document.") from exc

    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        # treat the first row as the header, same idea as the CSV rows
        header = [cell.text.strip() for cell in table.rows[0].cells]
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            lines.append("; ".join(f"{h}: {c}" for h, c in zip(header, cells, strict=False) if c) + ".")
    return "\n".join(lines)


def parse_file(filename, data):
    """Returns the list of passages for an uploaded file."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension == "pdf":
        passages = chunk_text(pdf_text(data))
    elif extension == "docx":
        passages = chunk_text(docx_text(data))
    else:
        text = data.decode("utf-8", errors="replace")
        if extension == "csv":
            passages = csv_passages(text)
        elif extension == "md":
            passages = chunk_text(clean_markdown(text))
        else:
            passages = chunk_text(text)

    if not passages:
        raise ParseError("No readable text found in this file.")
    return passages
