from app.ingestion.chunk import chunk_document
from app.ingestion.embed import embed_text
from app.ingestion.index import index_chunks
import pytest

def test_chunk_document():
    document = "This is a test document that needs to be chunked."
    chunks = chunk_document(document, chunk_size=10)
    assert len(chunks) == 5
    assert chunks[0] == "This is a "
    assert chunks[-1] == "chunked."

def test_embed_text():
    text = "This is a test text for embedding."
    embedding = embed_text(text)
    assert embedding is not None
    assert len(embedding) > 0

def test_index_chunks():
    chunks = [
        {"text": "Chunk 1", "metadata": {"id": 1}},
        {"text": "Chunk 2", "metadata": {"id": 2}},
    ]
    result = index_chunks(chunks)
    assert result is True  # Assuming the function returns True on success

@pytest.mark.parametrize("text,expected_length", [
    ("Short text.", 1),
    ("This is a longer text that should be chunked into multiple parts.", 3),
])
def test_chunk_document_parametrized(text, expected_length):
    chunks = chunk_document(text, chunk_size=10)
    assert len(chunks) == expected_length