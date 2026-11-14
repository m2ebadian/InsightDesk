from app.retriever import KnowledgeIndex, confidence_label

PASSAGES = [
    {
        "id": 1,
        "document_id": 1,
        "position": 1,
        "filename": "warranty.md",
        "text": "Standard parts are covered for 12 months. Premium parts are covered for 24 months.",
    },
    {
        "id": 2,
        "document_id": 2,
        "position": 1,
        "filename": "returns.txt",
        "text": "Unused parts can be returned within 30 days for a full refund.",
    },
    {
        "id": 3,
        "document_id": 3,
        "position": 1,
        "filename": "shipping.txt",
        "text": "Replacement orders ship with express shipping and arrive in 2 to 3 business days.",
    },
]


def make_index():
    index = KnowledgeIndex()
    index.rebuild(PASSAGES)
    return index


def test_confidence_label():
    assert confidence_label(0.5) == "high"
    assert confidence_label(0.2) == "medium"
    assert confidence_label(0.05) == "low"


def test_finds_the_right_passage():
    result = make_index().ask("How long are premium parts covered?")
    assert result["sources"][0]["filename"] == "warranty.md"
    assert "24 months" in result["answer"]
    assert "[1]" in result["answer"]
    assert result["confidence"] in ("high", "medium")


def test_unrelated_question_gets_no_answer():
    result = make_index().ask("What is the office wifi password?")
    assert result["sources"] == []
    assert result["confidence"] == "low"
    assert "couldn't find" in result["answer"]


def test_document_filter():
    result = make_index().ask("parts returned covered", top_k=3, document_ids=[2])
    assert {s["document_id"] for s in result["sources"]} == {2}


def test_empty_index():
    index = KnowledgeIndex()
    index.rebuild([])
    assert index.ask("anything")["sources"] == []


def test_only_stop_words():
    index = KnowledgeIndex()
    index.rebuild([{"id": 1, "document_id": 1, "position": 1, "filename": "x.txt", "text": "the and of"}])
    assert index.ask("the")["sources"] == []


def test_headings_are_not_used_as_answers():
    from app.retriever import is_real_sentence

    assert is_real_sentence("Claims under $500 can be approved by any agent.")
    assert not is_real_sentence("Warranty Policy")
    assert not is_real_sentence("Team lead.")


def test_question_mostly_about_something_else_is_low_confidence():
    # "parts" matches, but nothing about discounts or bulk pricing is in the documents
    result = make_index().ask("Is there a bulk discount on parts?")
    assert result["confidence"] == "low"
