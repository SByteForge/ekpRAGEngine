from typing import List
from app.ingestion.embedder import embed_text

def embed_chunks(chunks: List[str]) -> List[List[float]]:
    return [embed_text(chunk) for chunk in chunks]

def embed_and_index(chunks: List[str], index_function) -> None:
    embeddings = embed_chunks(chunks)
    for chunk, embedding in zip(chunks, embeddings):
        index_function(chunk, embedding)