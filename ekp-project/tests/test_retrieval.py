from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.dense import dense_retrieve
import pytest

def test_hybrid_retrieve():
    query = "Sample query"
    expected_result = "Expected document or chunk"
    
    result = hybrid_retrieve(query)
    
    assert result is not None
    assert expected_result in result

def test_dense_retrieve():
    query = "Another sample query"
    expected_result = "Expected dense document or chunk"
    
    result = dense_retrieve(query)
    
    assert result is not None
    assert expected_result in result

def test_retrieval_with_invalid_query():
    query = ""
    
    with pytest.raises(ValueError):
        hybrid_retrieve(query)
    
    with pytest.raises(ValueError):
        dense_retrieve(query)