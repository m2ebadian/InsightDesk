import pytest

from app.parsing import ParseError, chunk_text, clean_markdown, csv_passages, parse_file, split_sentences


def test_split_sentences():
    text = "First line without a period\nSecond one. Third one! Is this fourth?"
    assert split_sentences(text) == [
        "First line without a period",
        "Second one.",
        "Third one!",
        "Is this fourth?",
    ]


def test_chunk_text_keeps_sentences_whole_and_overlaps():
    sentences = [f"Sentence number {i} has exactly seven words." for i in range(30)]
    chunks = chunk_text(" ".join(sentences), max_words=30)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.endswith(".")
    # last sentence of a chunk is repeated at the start of the next one
    assert chunks[1].splitlines()[0] == chunks[0].splitlines()[-1]


def test_clean_markdown():
    assert clean_markdown("# Title\n- **bold** item\n`code`") == "Title\nbold item\ncode"


def test_csv_passages_have_rows_and_summaries():
    csv_text = "process,errors,hours\nLookup,18,6.2\nSearch,27,7.5\nShipping,12,4.1\n"
    passages = csv_passages(csv_text)
    assert passages[0] == "process: Lookup; errors: 18; hours: 6.2."
    assert len(passages) == 3 + 2  # 3 rows + 2 numeric columns
    assert "The highest errors is Search with 27." in passages[3]
    assert "The lowest hours is Shipping with 4.1." in passages[4]


def test_csv_with_no_rows():
    assert csv_passages("a,b\n") == []


def test_parse_docx(tmp_path):
    from docx import Document

    document = Document()
    document.add_paragraph("Escalate urgent tickets to the on-call team lead within one hour.")
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Level"
    table.rows[0].cells[1].text = "Owner"
    table.rows[1].cells[0].text = "Level 2"
    table.rows[1].cells[1].text = "Team lead"
    path = tmp_path / "test.docx"
    document.save(path)
    passages = parse_file("test.docx", path.read_bytes())
    assert "on-call team lead" in passages[0]
    assert "Level: Level 2; Owner: Team lead." in passages[0]


def test_parse_pdf():
    passages = parse_file("test.pdf", make_pdf("Refunds are processed within five business days."))
    assert "five business days" in passages[0]


def test_bad_pdf():
    with pytest.raises(ParseError):
        parse_file("broken.pdf", b"not really a pdf")


def test_empty_text_file():
    with pytest.raises(ParseError):
        parse_file("empty.txt", b"   \n  ")


def make_pdf(text):
    """Builds a tiny one-page PDF by hand so the tests don't need a PDF library."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out
