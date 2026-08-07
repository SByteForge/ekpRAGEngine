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

def dense_retrieve(query: str, top_k: int, tenant_id: str) -> List[RetrievedChunk]:
    # Embed the query
    query_embedding = embed_text(query)
    
    # Create a filter for tenant
    filter_condition = Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
        ]
    )
    
    # Perform the dense retrieval
    results = qdrant_client.search(
        collection_name=settings.COLLECTION_NAME,
        query_vector=query_embedding,
        filter=filter_condition,
        limit=top_k
    )
    
    # Process results into RetrievedChunk objects
    retrieved_chunks = [
        RetrievedChunk(
            qdrant_point_id=result.id,
            text=result.payload['text'],
            score=result.score,
            document_id=result.payload['document_id'],
            filename=result.payload['filename'],
            page_number=result.payload['page_number'],
            chunk_index=result.payload['chunk_index'],
            retriever="dense"
        )
        for result in results
    ]
    
    return retrieved_chunks