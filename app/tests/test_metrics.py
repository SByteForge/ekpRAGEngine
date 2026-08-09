from app.eval.metrics import recall_at_k, mrr, hit, precision_at_k, percentile


def make_result(document_id, page_number):
    return {"document_id": document_id, "page_number": page_number}


def test_recall_at_k_finds_match():
    retrieved = [make_result("doc1", 5), make_result("doc1", 10)]
    assert recall_at_k(retrieved, "doc1", 10) == 1.0


def test_recall_at_k_no_match():
    retrieved = [make_result("doc1", 5), make_result("doc1", 6)]
    assert recall_at_k(retrieved, "doc1", 10) == 0.0


def test_recall_at_k_empty_retrieval():
    assert recall_at_k([], "doc1", 10) == 0.0


def test_mrr_first_position():
    retrieved = [make_result("doc1", 10), make_result("doc2", 5)]
    assert mrr(retrieved, "doc1", 10) == 1.0


def test_mrr_third_position():
    retrieved = [make_result("doc2", 1), make_result("doc3", 2), make_result("doc1", 10)]
    assert mrr(retrieved, "doc1", 10) == 1.0 / 3


def test_mrr_no_match_returns_zero():
    retrieved = [make_result("doc2", 1)]
    assert mrr(retrieved, "doc1", 10) == 0.0


def test_hit_true_when_recall_positive():
    retrieved = [make_result("doc1", 10)]
    assert hit(retrieved, "doc1", 10) is True


def test_hit_false_when_no_match():
    retrieved = [make_result("doc2", 1)]
    assert hit(retrieved, "doc1", 10) is False


def test_precision_at_k_partial_match():
    retrieved = [make_result("doc1", 10), make_result("doc2", 1), make_result("doc3", 2)]
    assert precision_at_k(retrieved, "doc1", 10) == 1 / 3


def test_precision_at_k_empty():
    assert precision_at_k([], "doc1", 10) == 0.0


def test_percentile_p50_of_sorted_list():
    values = [10, 20, 30, 40, 50]
    assert percentile(values, 50) == 30


def test_percentile_empty_list():
    assert percentile([], 95) == 0.0


def test_percentile_p95_takes_near_max():
    values = list(range(1, 101))
    result = percentile(values, 95)
    assert result >= 90
