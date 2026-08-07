from typing import List, Optional


def is_relevant(retrieved_document_id, retrieved_page, gold_document_id, gold_page) -> bool:
    return retrieved_document_id == gold_document_id and retrieved_page == gold_page


def recall_at_k(retrieved: List[dict], gold_document_id: str, gold_page: Optional[int]) -> float:
    for r in retrieved:
        if is_relevant(r["document_id"], r["page_number"], gold_document_id, gold_page):
            return 1.0
    return 0.0


def mrr(retrieved: List[dict], gold_document_id: str, gold_page: Optional[int]) -> float:
    for rank, r in enumerate(retrieved, start=1):
        if is_relevant(r["document_id"], r["page_number"], gold_document_id, gold_page):
            return 1.0 / rank
    return 0.0


def hit(retrieved: List[dict], gold_document_id: str, gold_page: Optional[int]) -> bool:
    return recall_at_k(retrieved, gold_document_id, gold_page) == 1.0


def precision_at_k(retrieved: List[dict], gold_document_id: str, gold_page: Optional[int]) -> float:
    if not retrieved:
        return 0.0
    relevant_count = sum(1 for r in retrieved if is_relevant(r["document_id"], r["page_number"], gold_document_id, gold_page))
    return relevant_count / len(retrieved)


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(round((p / 100) * (len(sorted_vals) - 1)))
    return sorted_vals[idx]
