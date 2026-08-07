from typing import List
from app.ingestion.embed import embed_text
from app.ingestion.chunk import chunk_documents
from app.ingestion.indexer import _client as qdrant_client

def index_documents(documents: List[str], tenant_id: str) -> None:
    chunks = []
    for doc in documents:
        chunks.extend(chunk_documents(doc, tenant_id))
    
    embedded_chunks = embed_text(chunks)
    
    for chunk in embedded_chunks:
        qdrant_client.index(chunk)