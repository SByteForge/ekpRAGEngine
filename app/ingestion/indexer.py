import uuid
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from app.core.config import settings
 
_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
EMBED_DIM = 768
 
 
def ensure_collection():
    collections = [c.name for c in _client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        _client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        _client.create_payload_index(settings.qdrant_collection, "tenant_id", PayloadSchemaType.KEYWORD)
        _client.create_payload_index(settings.qdrant_collection, "document_id", PayloadSchemaType.KEYWORD)
 
 
def upsert_chunks(tenant_id, document_id, chunk_texts, chunk_vectors, chunk_metadata) -> List[str]:
    ensure_collection()
    point_ids = [str(uuid.uuid4()) for _ in chunk_texts]
    points = [
        PointStruct(
            id=point_ids[i],
            vector=chunk_vectors[i],
            payload={"tenant_id": tenant_id, "document_id": document_id, "text": chunk_texts[i], **chunk_metadata[i]},
        )
        for i in range(len(chunk_texts))
    ]
    _client.upsert(collection_name=settings.qdrant_collection, points=points)
    return point_ids
