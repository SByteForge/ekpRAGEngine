from typing import List
from sqlalchemy.orm import Session
from app.core.logging import timed_stage
from app.core.config import settings
from app.retrieval.dense import dense_search, RetrievedChunk
from app.retrieval.bm25 import bm25_search
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import rerank


def hybrid_retrieve(db: Session, query: str, tenant_id: str, top_k_final: int = None) -> List[RetrievedChunk]:
    top_k_final = top_k_final or settings.retrieval_top_k_final

    with timed_stage("retrieval.dense", tenant_id=tenant_id, query=query) as ctx:
        dense_results = dense_search(query, tenant_id)
        ctx["n_results"] = len(dense_results)

    with timed_stage("retrieval.bm25", tenant_id=tenant_id, query=query) as ctx:
        bm25_results = bm25_search(db, query, tenant_id)
        ctx["n_results"] = len(bm25_results)

    with timed_stage("retrieval.fuse", tenant_id=tenant_id) as ctx:
        fused = reciprocal_rank_fusion(dense_results, bm25_results)
        ctx["n_fused"] = len(fused)
        if not fused:
            ctx["error_reason"] = "no_results_from_either_retriever"

    with timed_stage("retrieval.rerank", tenant_id=tenant_id) as ctx:
        reranked = rerank(query, fused, top_k=top_k_final)
        ctx["n_final"] = len(reranked)

    return reranked
