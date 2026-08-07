import argparse
import json
import random
from pathlib import Path
import ollama
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.db_models import DocumentChunk, Document

_client = ollama.Client(host=settings.ollama_base_url)

QUESTION_GEN_PROMPT = """Read this excerpt from a document and write ONE specific, \
factual question that this excerpt directly answers. The question should be \
answerable using ONLY this excerpt's content. Respond with ONLY the question text, \
nothing else - no preamble, no quotes.

Excerpt:
{text}

Question:"""


def generate_golden_set(tenant_id: str, n: int, output_path: str):
    db = SessionLocal()
    try:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.tenant_id == tenant_id)
            .filter(DocumentChunk.token_count > 80)
            .all()
        )
        if not chunks:
            print(f"No chunks found for tenant {tenant_id}. Ingest documents first.")
            return

        sample = random.sample(chunks, min(n, len(chunks)))
        docs = {d.id: d.filename for d in db.query(Document).filter(
            Document.id.in_({c.document_id for c in sample})
        ).all()}

        golden_set = []
        for i, chunk in enumerate(sample):
            try:
                response = _client.generate(
                    model=settings.ollama_gen_model,
                    prompt=QUESTION_GEN_PROMPT.format(text=chunk.text),
                    stream=False,
                )
                question = response["response"].strip().strip('"')
                golden_set.append({
                    "id": f"q{i+1}", "question": question,
                    "expected_document_id": chunk.document_id,
                    "expected_filename": docs.get(chunk.document_id, ""),
                    "expected_page_number": chunk.page_number,
                    "source_excerpt": chunk.text[:300],
                })
                print(f"[{i+1}/{len(sample)}] {question}")
            except Exception as e:
                print(f"[{i+1}/{len(sample)}] FAILED: {e}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(golden_set, f, indent=2)

        print(f"\nWrote {len(golden_set)} questions to {output_path}")
        print("Review and edit these before the interview - some auto-generated")
        print("questions may be too trivial or ambiguous. Delete/rewrite as needed.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--n", type=int, default=15)
    parser.add_argument("--output", default="golden_set/qa.json")
    args = parser.parse_args()
    generate_golden_set(args.tenant_id, args.n, args.output)
