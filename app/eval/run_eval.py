import argparse
import json
import time
import uuid
from pathlib import Path
from app.core.db import SessionLocal
from app.core.db_models import Tenant, EvaluationResult
from app.retrieval.hybrid import hybrid_retrieve
from app.generation.prompt import build_prompt
from app.generation.llm_client import generate
from app.generation.citations import extract_citations
from app.eval.metrics import recall_at_k, mrr, hit, percentile
from app.eval.llm_judge import judge_faithfulness


def run_eval(tenant_id: str, golden_set_path: str, output_dir: str = "golden_set"):
    with open(golden_set_path) as f:
        golden_set = json.load(f)
    if not golden_set:
        print("Golden set is empty. Run generate_golden_set.py first.")
        return

    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        print(f"Unknown tenant_id: {tenant_id}")
        return

    run_id = str(uuid.uuid4())[:8]
    results = []
    retrieval_latencies, generation_latencies, total_latencies = [], [], []
    n_success, n_failed = 0, 0

    print(f"Running eval (run_id={run_id}) on {len(golden_set)} questions...\n")

    for i, item in enumerate(golden_set):
        question = item["question"]
        gold_doc_id = item["expected_document_id"]
        gold_page = item["expected_page_number"]
        print(f"[{i+1}/{len(golden_set)}] {question}")

        eval_row = EvaluationResult(run_id=run_id, question=question, expected_answer=item.get("source_excerpt"))

        try:
            t0 = time.perf_counter()
            chunks = hybrid_retrieve(db, query=question, tenant_id=tenant_id)
            t1 = time.perf_counter()
            retrieval_ms = (t1 - t0) * 1000
            retrieval_latencies.append(retrieval_ms)

            retrieved_for_metrics = [{"document_id": c.document_id, "page_number": c.page_number} for c in chunks]
            r_at_k = recall_at_k(retrieved_for_metrics, gold_doc_id, gold_page)
            r_mrr = mrr(retrieved_for_metrics, gold_doc_id, gold_page)
            r_hit = hit(retrieved_for_metrics, gold_doc_id, gold_page)

            if not chunks:
                raise ValueError("empty_retrieval")

            prompt = build_prompt(question, chunks)
            t2 = time.perf_counter()
            answer = generate(prompt)
            t3 = time.perf_counter()
            generation_ms = (t3 - t2) * 1000
            generation_latencies.append(generation_ms)

            citation_data = extract_citations(answer, chunks)
            judge_result = judge_faithfulness(question, answer, [{"text": c.text} for c in chunks])

            total_ms = retrieval_ms + generation_ms
            total_latencies.append(total_ms)

            eval_row.generated_answer = answer
            eval_row.retrieved_chunk_ids = [c.qdrant_point_id for c in chunks]
            eval_row.recall_at_k = r_at_k
            eval_row.mrr = r_mrr
            eval_row.hit = r_hit
            eval_row.faithfulness_score = judge_result["faithfulness_score"]
            eval_row.hallucination_flag = judge_result["hallucination"]
            eval_row.citation_accuracy = citation_data["citation_accuracy"]
            eval_row.retrieval_latency_ms = retrieval_ms
            eval_row.generation_latency_ms = generation_ms
            eval_row.total_latency_ms = total_ms
            eval_row.success = True
            n_success += 1
            print(f"    hit={r_hit} mrr={r_mrr:.2f} faithfulness={judge_result['faithfulness_score']} retrieval={retrieval_ms:.0f}ms generation={generation_ms:.0f}ms")

        except Exception as e:
            eval_row.success = False
            eval_row.error_reason = f"{type(e).__name__}: {e}"
            n_failed += 1
            print(f"    FAILED: {eval_row.error_reason}")

        db.add(eval_row)
        db.commit()
        results.append({
            "question": question, "success": eval_row.success, "error_reason": eval_row.error_reason,
            "recall_at_k": eval_row.recall_at_k, "mrr": eval_row.mrr, "hit": eval_row.hit,
            "faithfulness_score": eval_row.faithfulness_score, "hallucination_flag": eval_row.hallucination_flag,
            "citation_accuracy": eval_row.citation_accuracy, "retrieval_latency_ms": eval_row.retrieval_latency_ms,
            "generation_latency_ms": eval_row.generation_latency_ms, "generated_answer": eval_row.generated_answer,
        })

    n_total = len(golden_set)
    successful = [r for r in results if r["success"]]
    faithfulness_scores = [r["faithfulness_score"] for r in successful if r["faithfulness_score"] is not None]
    hallucinations = [r["hallucination_flag"] for r in successful if r["hallucination_flag"] is not None]
    citation_accuracies = [r["citation_accuracy"] for r in successful if r["citation_accuracy"] is not None]

    summary = {
        "run_id": run_id, "n_total": n_total, "n_success": n_success, "n_failed": n_failed,
        "failure_rate": round(n_failed / n_total, 3) if n_total else None,
        "retrieval": {
            "recall_at_k_mean": round(sum(r["recall_at_k"] for r in successful) / len(successful), 3) if successful else None,
            "mrr_mean": round(sum(r["mrr"] for r in successful) / len(successful), 3) if successful else None,
            "hit_rate": round(sum(1 for r in successful if r["hit"]) / len(successful), 3) if successful else None,
        },
        "generation": {
            "faithfulness_mean": round(sum(faithfulness_scores) / len(faithfulness_scores), 3) if faithfulness_scores else None,
            "hallucination_rate": round(sum(hallucinations) / len(hallucinations), 3) if hallucinations else None,
            "citation_accuracy_mean": round(sum(citation_accuracies) / len(citation_accuracies), 3) if citation_accuracies else None,
        },
        "latency_ms": {
            "retrieval_p50": round(percentile(retrieval_latencies, 50), 1), "retrieval_p95": round(percentile(retrieval_latencies, 95), 1),
            "generation_p50": round(percentile(generation_latencies, 50), 1), "generation_p95": round(percentile(generation_latencies, 95), 1),
            "total_p50": round(percentile(total_latencies, 50), 1), "total_p95": round(percentile(total_latencies, 95), 1),
        },
    }

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(output_dir) / f"eval_report_{run_id}.json"
    with open(report_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print("\n" + "=" * 60)
    print(f"EVAL SUMMARY (run_id={run_id})")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print(f"\nFull report written to: {report_path}")
    db.close()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--golden-set", default="golden_set/qa.json")
    parser.add_argument("--output-dir", default="golden_set")
    args = parser.parse_args()
    run_eval(args.tenant_id, args.golden_set, args.output_dir)
