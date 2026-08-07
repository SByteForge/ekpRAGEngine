from typing import List, Dict
from app.retrieval.dense import RetrievedChunk

RRF_K = 60


def reciprocal_rank_fusion(dense_results: List[RetrievedChunk], bm25_results: List[RetrievedChunk]) -> List[RetrievedChunk]:
    scores: Dict[str, float] = {}
    chunk_by_id: Dict[str, RetrievedChunk] = {}
    retrievers_hit: Dict[str, set] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        pid = chunk.qdrant_point_id
        scores[pid] = scores.get(pid, 0) + 1.0 / (RRF_K + rank)
        chunk_by_id[pid] = chunk
        retrievers_hit.setdefault(pid, set()).add("dense")

    for rank, chunk in enumerate(bm25_results, start=1):
        pid = chunk.qdrant_point_id
        scores[pid] = scores.get(pid, 0) + 1.0 / (RRF_K + rank)
        if pid not in chunk_by_id:
            chunk_by_id[pid] = chunk
        retrievers_hit.setdefault(pid, set()).add("bm25")

    fused = []
    for pid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        chunk = chunk_by_id[pid]
        chunk.score = score
        chunk.retriever = "+".join(sorted(retrievers_hit[pid]))
        fused.append(chunk)
    return fused
