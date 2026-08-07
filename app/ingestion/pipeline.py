from pathlib import Path
from sqlalchemy.orm import Session
from app.core.logging import timed_stage, log
from app.core.db_models import Document, DocumentChunk
from app.ingestion.parsers import parse_document
from app.ingestion.chunker import chunk_pages
from app.ingestion.embedder import embed_batch
from app.ingestion.indexer import upsert_chunks
 
 
def ingest_document(db: Session, document: Document, file_path: Path) -> Document:
    tenant_id = document.tenant_id
    document.status = "processing"
    db.commit()
    try:
        with timed_stage("ingestion.parse", tenant_id=tenant_id, filename=document.filename) as ctx:
            pages = parse_document(file_path)
            ctx["n_pages"] = len(pages)
            if not pages:
                raise ValueError("Parser returned no extractable text")
 
        with timed_stage("ingestion.chunk", tenant_id=tenant_id, filename=document.filename) as ctx:
            chunks = chunk_pages(pages)
            ctx["n_chunks"] = len(chunks)
            if not chunks:
                raise ValueError("Chunker produced zero chunks from parsed pages")
 
        with timed_stage("ingestion.embed", tenant_id=tenant_id, filename=document.filename) as ctx:
            vectors = embed_batch([c.text for c in chunks])
            ctx["n_vectors"] = len(vectors)
 
        with timed_stage("ingestion.index", tenant_id=tenant_id, filename=document.filename) as ctx:
            metadata = [
                {"chunk_index": c.chunk_index, "page_number": c.page_number, "filename": document.filename,
                 "source_category": document.source_category, "doc_type": document.doc_type}
                for c in chunks
            ]
            point_ids = upsert_chunks(tenant_id, document.id, [c.text for c in chunks], vectors, metadata)
            ctx["n_indexed"] = len(point_ids)
 
        for c, point_id in zip(chunks, point_ids):
            db.add(DocumentChunk(document_id=document.id, tenant_id=tenant_id, chunk_index=c.chunk_index,
                                  text=c.text, token_count=c.token_count, page_number=c.page_number,
                                  qdrant_point_id=point_id))
 
        document.status = "indexed"
        document.n_chunks = len(chunks)
        document.error_reason = None
        db.commit()
        db.refresh(document)
        return document
    except Exception as e:
        db.rollback()
        document.status = "failed"
        document.error_reason = f"{type(e).__name__}: {e}"
        db.commit()
        log.event("ingestion.pipeline", latency_ms=0, success=False, tenant_id=tenant_id,
                   error_reason=document.error_reason, filename=document.filename)
        db.refresh(document)
        return document
