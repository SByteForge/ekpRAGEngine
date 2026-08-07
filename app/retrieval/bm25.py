from dataclasses import dataclass
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db_models import DocumentChunk, Document
from app.retrieval.dense import RetrievedChunk

_cache: Dict[str, Tuple[int, BM25Okapi, List[DocumentChunk]]] = {}


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _get_or_build_index(db: Session, tenant_id: str):
    current_count = db.query(DocumentChunk).filter(DocumentChunk.tenant_id == tenant_id).count()
    cached = _cache.get(tenant_id)
    if cached and cached[0] == current_count:
        return cached[1], cached[2]
    chunks = db.query(DocumentChunk).filter(DocumentChunk.tenant_id == tenant_id).all()
    tokenized_corpus = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    _cache[tenant_id] = (current_count, bm25, chunks)
    return bm25, chunks


def bm25_search(db: Session, query: str, tenant_id: str, top_k: int = None) -> List[RetrievedChunk]:
    top_k = top_k or settings.retrieval_top_k_bm25
    bm25, chunks = _get_or_build_index(db, tenant_id)
    if bm25 is None or not chunks:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
    doc_ids = {c.document_id for c, _ in ranked}
    docs = {d.id: d.filename for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
    return [
        RetrievedChunk(
            qdrant_point_id=c.qdrant_point_id, text=c.text, score=float(score),
            document_id=c.document_id, filename=docs.get(c.document_id, ""),
            page_number=c.page_number, chunk_index=c.chunk_index, retriever="bm25",
        )
        for c, score in ranked if score > 0
    ]
