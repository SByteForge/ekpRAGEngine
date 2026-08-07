from typing import List
from app.retrieval.dense import DenseRetriever
from app.retrieval.bm25 import BM25Retriever
from app.core.config import settings
from app.ingestion.embedder import embed_text

class HybridRetriever:
    def __init__(self):
        self.dense_retriever = DenseRetriever()
        self.bm25_retriever = BM25Retriever()

    def retrieve(self, query: str, top_k: int) -> List[dict]:
        dense_results = self.dense_retriever.retrieve(query, top_k)
        bm25_results = self.bm25_retriever.retrieve(query, top_k)

        # Combine results from both retrievers
        combined_results = self.combine_results(dense_results, bm25_results)
        return combined_results

    def combine_results(self, dense_results: List[dict], bm25_results: List[dict]) -> List[dict]:
        # Logic to combine and rank results from both retrieval methods
        # This can include merging, deduplication, and scoring adjustments
        combined = {result['document_id']: result for result in dense_results}

        for result in bm25_results:
            if result['document_id'] not in combined:
                combined[result['document_id']] = result
            else:
                combined[result['document_id']]['score'] += result['score']

        return list(combined.values())[:10]  # Return top 10 results