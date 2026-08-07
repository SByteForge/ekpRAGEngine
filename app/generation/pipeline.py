from sqlalchemy.orm import Session
from app.core.logging import timed_stage
from app.retrieval.hybrid import hybrid_retrieve
from app.generation.prompt import build_prompt
from app.generation.llm_client import generate
from app.generation.citations import extract_citations


def answer_question(db: Session, question: str, tenant_id: str) -> dict:
    chunks = hybrid_retrieve(db, query=question, tenant_id=tenant_id)

    if not chunks:
        return {
            "answer": "I couldn't find any relevant information in the indexed documents to answer this question.",
            "citations": [], "invalid_citation_markers": [], "citation_accuracy": None,
            "retrieved_chunks": [], "success": True, "error_reason": "empty_retrieval",
        }

    with timed_stage("generation.prompt_build", tenant_id=tenant_id) as ctx:
        prompt = build_prompt(question, chunks)
        ctx["prompt_length_chars"] = len(prompt)

    with timed_stage("generation.llm_call", tenant_id=tenant_id) as ctx:
        answer = generate(prompt)
        ctx["answer_length_chars"] = len(answer)

    with timed_stage("generation.citation_extraction", tenant_id=tenant_id) as ctx:
        citation_data = extract_citations(answer, chunks)
        ctx["n_citations"] = citation_data["n_sources_cited"]

    return {
        "answer": answer,
        "citations": citation_data["citations"],
        "invalid_citation_markers": citation_data["invalid_citation_markers"],
        "citation_accuracy": citation_data["citation_accuracy"],
        "retrieved_chunks": [
            {"text": c.text[:300], "filename": c.filename, "page_number": c.page_number,
             "retriever": c.retriever, "score": round(c.score, 4)}
            for c in chunks
        ],
        "success": True, "error_reason": None,
    }
