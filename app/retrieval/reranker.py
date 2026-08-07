from typing import List
from app.core.config import settings
from app.retrieval.dense import RetrievedChunk

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(settings.rerank_model)
    return _model


def rerank(query: str, candidates: List[RetrievedChunk], top_k: int = None) -> List[RetrievedChunk]:
    top_k = top_k or settings.retrieval_top_k_final
    if not candidates:
        return []
    model = _get_model()
    pairs = [(query, c.text) for c in candidates]
    ce_scores = model.predict(pairs)
    for chunk, ce_score in zip(candidates, ce_scores):
        chunk.score = float(ce_score)
    reranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    return reranked[:top_k]
