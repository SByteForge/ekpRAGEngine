from typing import List
from dataclasses import dataclass
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.ingestion.indexer import _client as qdrant_client
from app.ingestion.embedder import embed_text


@dataclass
class RetrievedChunk:
    qdrant_point_id: str
    text: str
    score: float
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    retriever: str


def dense_search(query: str, tenant_id: str, top_k: int = None) -> List[RetrievedChunk]:
    top_k = top_k or settings.retrieval_top_k_dense
    query_vector = embed_text(query)
    results = qdrant_client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]),
        limit=top_k,
    )
    return [
        RetrievedChunk(
            qdrant_point_id=str(r.id), text=r.payload.get("text", ""), score=r.score,
            document_id=r.payload.get("document_id", ""), filename=r.payload.get("filename", ""),
            page_number=r.payload.get("page_number"), chunk_index=r.payload.get("chunk_index"),
            retriever="dense",
        )
        for r in results
    ]
