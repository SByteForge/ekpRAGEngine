import re
from typing import List, Dict
from app.retrieval.dense import RetrievedChunk

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def extract_citations(answer: str, chunks: List[RetrievedChunk]) -> Dict:
    cited_indices = sorted({int(m) for m in CITATION_PATTERN.findall(answer)})
    valid_citations = []
    invalid_citations = []
    for idx in cited_indices:
        if 1 <= idx <= len(chunks):
            chunk = chunks[idx - 1]
            valid_citations.append({
                "marker": idx, "document_id": chunk.document_id, "filename": chunk.filename,
                "page_number": chunk.page_number, "snippet": chunk.text[:200],
            })
        else:
            invalid_citations.append(idx)
    citation_accuracy = len(valid_citations) / len(cited_indices) if cited_indices else None
    return {
        "citations": valid_citations, "invalid_citation_markers": invalid_citations,
        "citation_accuracy": citation_accuracy, "n_sources_cited": len(valid_citations),
        "n_sources_provided": len(chunks),
    }
