# Enterprise Knowledge Platform (EKP)

A multi-tenant **Retrieval-Augmented Generation** service. Point it at your
organization's private documents (PDF / Markdown / DOCX) and ask
natural-language questions — answers come back grounded in your corpus with
inline `[N]` citations resolved to a specific document and page. Runs fully
local: Postgres + Qdrant + Ollama, no data leaves the deployment.

> **Architecture, data model, and design rationale:** see [`docs/DESIGN.md`](docs/DESIGN.md).

---

## Highlights

- **Hybrid retrieval** — dense (Qdrant) + BM25, fused with Reciprocal Rank Fusion, reranked by a `bge-reranker-base` cross-encoder.
- **Grounded generation** — strict prompt that answers only from retrieved excerpts; every claim carries a `[N]` citation, validated against the source set with a reported citation-accuracy score.
- **Multi-tenant isolation** — per-tenant API keys (salted SHA-256), tenant filter enforced at the vector-store and relational layers.
- **Evaluation harness** — golden-set retrieval metrics (recall@k, MRR, hit rate), LLM-as-judge faithfulness + hallucination rate, and p50/p95 latency, written to a JSON report.
- **Observability** — every pipeline stage emits a structured JSON event with latency and success.
- **Demo UI** — Streamlit Chat tab + a "Quality & Trust" dashboard that explains each metric in plain English.

---

## Architecture at a glance

```
Streamlit UI / API clients
        │
   FastAPI (app.main)
   /tenants /users /documents/ingest /search /chat
        │
   ┌────┴─────────────┬──────────────────┐
 Ingestion         Retrieval          Generation
 parse→chunk→      dense + bm25 →      prompt → Ollama LLM
 embed→index       RRF → rerank       → citation extraction
        │                │                    │
   Postgres          Qdrant               Ollama
 (metadata,       (vectors +           (gen / embed /
  chunks,          tenant-filtered      judge models)
  conversations,   payload)
  eval results)
```

---

## Quickstart

### Prerequisites
- Docker + Docker Compose
- [Ollama](https://ollama.com) running on the host with the models pulled:
  ```bash
  ollama pull llama3.1:8b        # generation
  ollama pull nomic-embed-text   # embeddings
  ollama pull llama3.2:3b        # eval judge
  ```

### Run
```bash
cp .env.example .env            # then edit secrets (API_KEY_SALT, JWT_SECRET)
docker compose up --build
```
- API: http://localhost:8000  (`GET /health` → `{"status":"ok"}`)
- Postgres: `localhost:5432`, Qdrant: `localhost:6333`

### Demo UI
```bash
pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
```

---

## API walkthrough

```bash
# 1. Create a tenant
curl -s -X POST localhost:8000/tenants -F name=acme

# 2. Issue an API key for a user (raw key is shown once)
curl -s -X POST localhost:8000/users -F tenant_id=<TENANT_ID> -F email=you@acme.com

# 3. Ingest a document
curl -s -X POST localhost:8000/documents/ingest \
  -H "Authorization: Bearer <API_KEY>" \
  -F tenant_id=<TENANT_ID> -F source_category=hr \
  -F file=@handbook.pdf

# 4. Ask a question
curl -s -X POST localhost:8000/chat \
  -H "Authorization: Bearer <API_KEY>" \
  -F tenant_id=<TENANT_ID> \
  -F question="How many personal days do full-time staff get?"
```

`/chat` returns the answer, resolved citations (`document`, `page`, `snippet`),
any invalid citation markers, the citation-accuracy score, and previews of the
retrieved chunks.

---

## Evaluation

```bash
# Generate a golden set from an ingested tenant's corpus (review before use)
python -m app.eval.generate_golden_set --tenant-id <TENANT_ID> --n 15

# Run the harness → prints a summary, writes golden_set/eval_report_<run_id>.json
python -m app.eval.run_eval --tenant-id <TENANT_ID>
```

Metrics: recall@k, MRR, hit rate (retrieval); faithfulness, hallucination rate,
citation accuracy (generation); retrieval / generation / total latency p50 & p95.

---

## Tests

```bash
python -m pytest app/tests/ -v
```

CI (`.github/workflows/ci.yml`) runs the unit tests, builds the Docker image,
and smoke-tests `/health` against the built container on every push / PR to `main`.

---

## Project layout

```
app/
  main.py            FastAPI app + endpoints
  core/              config, db, ORM models, structured logging
  tenancy/           API-key auth + tenant guard
  ingestion/         parsers, chunker, embedder, indexer, pipeline
  retrieval/         dense, bm25, fusion, reranker, hybrid
  generation/        prompt, llm_client, citations, pipeline
  eval/              golden-set generation, metrics, LLM judge, run_eval
  tests/             unit tests (auth, metrics, citations)
frontend/            Streamlit demo UI
golden_set/          checked-in evaluation set
docs/DESIGN.md       full design document
```

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)).
Notable knobs: `OLLAMA_GEN_MODEL` (swap the generation model with one env change),
`CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS`, and
`RETRIEVAL_TOP_K_DENSE` / `_BM25` / `_FINAL`.
