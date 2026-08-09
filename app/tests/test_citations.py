from dataclasses import dataclass
from app.generation.citations import extract_citations


@dataclass
class FakeChunk:
    document_id: str
    filename: str
    page_number: int
    text: str


def make_chunks(n=3):
    return [
        FakeChunk(document_id=f"doc{i}", filename=f"file{i}.pdf", page_number=i, text=f"content {i}" * 20)
        for i in range(1, n + 1)
    ]


def test_extracts_single_valid_citation():
    chunks = make_chunks(3)
    result = extract_citations("The policy states X [1].", chunks)
    assert result["n_sources_cited"] == 1
    assert result["citations"][0]["document_id"] == "doc1"
    assert result["citation_accuracy"] == 1.0


def test_extracts_multiple_valid_citations():
    chunks = make_chunks(3)
    result = extract_citations("First point [1]. Second point [2].", chunks)
    assert result["n_sources_cited"] == 2
    assert result["citation_accuracy"] == 1.0


def test_flags_invalid_citation_out_of_range():
    chunks = make_chunks(2)
    result = extract_citations("According to source [5].", chunks)
    assert result["n_sources_cited"] == 0
    assert 5 in result["invalid_citation_markers"]
    assert result["citation_accuracy"] == 0.0


def test_mixed_valid_and_invalid_citations():
    chunks = make_chunks(2)
    result = extract_citations("Valid [1] but also invented [9].", chunks)
    assert result["n_sources_cited"] == 1
    assert 9 in result["invalid_citation_markers"]
    assert result["citation_accuracy"] == 0.5


def test_no_citations_in_answer():
    chunks = make_chunks(3)
    result = extract_citations("I don't have enough information to answer.", chunks)
    assert result["n_sources_cited"] == 0
    assert result["citation_accuracy"] is None


def test_duplicate_citation_markers_counted_once():
    chunks = make_chunks(2)
    result = extract_citations("As shown [1], and again [1] later.", chunks)
    assert result["n_sources_cited"] == 1
