# Enterprise Knowledge Platform (EKP) — Design Document

**Status:** v1 (Phases 0–9 complete) · **Author:** Shubham Tiwari · **Last updated:** 2026-09-07

A multi-tenant Retrieval-Augmented Generation (RAG) service that lets an
organization ask natural-language questions against its own private documents
and get back answers with inline, verifiable citations — plus a measured,
transparent view of how trustworthy those answers are.

---

## 1. Problem & Motivation

Enterprises accumulate large volumes of unstructured knowledge (handbooks,
policies, SOPs, contracts) that employees cannot search effectively. Generic
LLM chat tools don't know this content and hallucinate when asked about it.
The goal of EKP is to deliver a system that:

1. **Answers only from the customer's own corpus** — no outside knowledge, no guessing.
2. **Cites every claim** back to a specific document and page, so a human can verify it.
3. **Isolates tenants** — one customer can never retrieve another customer's data.
4. **Measures its own quality** — retrieval accuracy, faithfulness, hallucination
   rate, citation accuracy, and latency are continuously evaluated against a
   golden set rather than asserted.
5. **Runs fully locally / on-prem** — Postgres, Qdrant, and Ollama; no data leaves the deployment.

### Non-goals (v1)
- Real-time document sync / connectors (Confluence, SharePoint, GDrive).
- Streaming token responses in the UI.
- Role-based access *within* a tenant (all users of a tenant see all tenant docs).
- Horizontal scale-out / HA; v1 targets a single-node deployment.
- Fine-tuning or hosting custom models.

---

## 2. Requirements

### Functional
| # | Requirement |
|---|---|
| F1 | Ingest PDF, Markdown, and DOCX documents via an authenticated API. |
| F2 | Parse → chunk → embed → index each document; expose ingestion status and failure reasons. |
| F3 | Hybrid retrieval (dense + lexical) with fusion and cross-encoder reranking. |
| F4 | Generate grounded answers with `[N]` inline citations resolved to `{document, page, snippet}`. |
| F5 | Persist conversations and messages for follow-up context. |
| F6 | Per-tenant API-key auth; reject cross-tenant access. |
| F7 | Offline eval harness producing retrieval, generation, and latency metrics + a JSON report. |
| F8 | Demo UI with a Chat tab and a "Quality & Trust" tab explaining each metric in plain English. |

### Non-functional
- **Isolation:** tenant filter enforced at the vector-store query level and the relational level.
- **Observability:** every pipeline stage emits a structured JSON event with latency + success.
- **Reliability:** ingestion failures are captured per-document, never crash the request; LLM/embedding calls retry with exponential backoff.
- **Reproducibility:** pinned dependencies, Dockerized, CI runs unit tests + image build + health smoke test.
- **Portability:** swapping the generation model is a single env var change.

---

## 3. High-Level Architecture

```
                       ┌──────────────────────────┐
   Streamlit UI  ───►  │   FastAPI  (app.main)    │
   / API clients       │                          │
                       │  /tenants  /users        │
                       │  /documents/ingest       │
                       │  /search   /chat         │
                       └───┬─────────┬────────┬───┘
                           │         │        │
              ┌────────────▼──┐  ┌───▼─────┐  ┌▼─────────────┐
              │  Ingestion    │  │Retrieval│  │  Generation  │
              │  pipeline     │  │ hybrid  │  │  pipeline    │
              └───┬───────┬───┘  └──┬───┬──┘  └──────┬───────┘
                  │       │         │   │            │
        parse/chunk/embed │     dense│   │bm25    build prompt
                  │       │         │   │        → Ollama LLM
                  ▼       ▼         ▼   ▼            ▼
              ┌────────┐ ┌──────────────┐   ┌───────────────┐
              │Postgres│ │   Qdrant     │   │  Ollama       │
              │(metadata│ │ (vectors +   │   │ (gen / embed /│
              │ chunks, │ │  payload,    │   │  judge models)│
              │ convos, │ │  tenant idx) │   └───────────────┘
              │ eval)   │ └──────────────┘
              └────────┘
```

### Component responsibilities

| Layer | Module(s) | Responsibility |
|---|---|---|
| API | `app/main.py` | HTTP surface, request validation, orchestration, conversation persistence |
| Tenancy / Auth | `app/tenancy/auth.py` | API-key generation, SHA-256 salted hashing, bearer-token resolution, tenant-match guard |
| Ingestion | `app/ingestion/{parsers,chunker,embedder,indexer,pipeline}.py` | Document → text → token-windowed chunks → embeddings → Qdrant points + Postgres rows |
| Retrieval | `app/retrieval/{dense,bm25,fusion,reranker,hybrid}.py` | Dense (Qdrant) + BM25 (in-proc) candidates → RRF → cross-encoder rerank → top-K |
| Generation | `app/generation/{prompt,llm_client,citations,pipeline}.py` | Grounded prompt assembly, LLM call, `[N]` citation extraction & validation |
| Evaluation | `app/eval/{generate_golden_set,metrics,llm_judge,run_eval}.py` | Golden-set creation, retrieval metrics, LLM-as-judge faithfulness, latency percentiles, report |
| Core | `app/core/{config,db,db_models,logging}.py` | Settings, SQLAlchemy engine/session, ORM models, structured timed-stage logging |
| Persistence | Postgres 16, Qdrant 1.11 | Relational metadata / vector index |
| Models | Ollama (`llama3.1:8b` gen, `nomic-embed-text` embed, `llama3.2:3b` judge) | Local inference |
| UI | `frontend/streamlit_app.py` | Chat + Quality & Trust dashboard |

---

## 4. Data Model (Postgres)

All IDs are string UUIDs. Tenant scoping columns are indexed.

- **tenants** `(id, name unique, created_at)`
- **users** `(id, tenant_id→tenants, email unique, hashed_api_key, created_at)`
- **documents** `(id, tenant_id→tenants, filename, doc_type, source_category, status, error_reason, n_chunks, created_at, indexed_at)`
  - `status ∈ {pending, processing, indexed, failed}`
- **document_chunks** `(id, document_id→documents, tenant_id, chunk_index, text, token_count, page_number, qdrant_point_id unique, created_at)`
- **conversations** `(id, tenant_id, user_id?, created_at)`
- **messages** `(id, conversation_id→conversations, role, content, citations JSON, created_at)`
- **evaluation_results** `(id, run_id, question, expected/generated_answer, retrieved_chunk_ids JSON, recall_at_k, mrr, hit, faithfulness_score, hallucination_flag, citation_accuracy, retrieval/generation/total_latency_ms, success, error_reason, created_at)`

**Qdrant** collection `ekp_chunks`: 768-dim cosine vectors; payload carries
`tenant_id, document_id, text, chunk_index, page_number, filename,
source_category, doc_type`. Keyword payload indexes on `tenant_id` and
`document_id`. Postgres is the source of truth for chunk metadata; Qdrant point
IDs are the join key.

Schema is created on startup via `Base.metadata.create_all`; Alembic is wired
(`db/migrations`) for forward migrations.

---

## 5. Key Flows

### 5.1 Ingestion (`POST /documents/ingest`)
1. Auth → `require_tenant_match(user, tenant_id)`.
2. Validate extension (`.pdf/.md/.markdown/.docx`); save file under `data/corpus/<tenant_id>/`.
3. Create `documents` row (`status=pending`).
4. `ingest_document()` runs synchronously through four timed stages:
   - **parse** — per-parser extraction; PDF keeps page numbers, MD/DOCX are single-page.
   - **chunk** — `tiktoken` `cl100k_base`, 512-token windows / 64-token overlap, page number carried per chunk.
   - **embed** — `nomic-embed-text` via Ollama, per-chunk, retried 3× exp-backoff.
   - **index** — upsert `PointStruct`s into Qdrant; ensure collection + payload indexes exist.
5. Persist `document_chunks` rows; set `status=indexed`, `n_chunks`.
6. Any exception → rollback, `status=failed`, `error_reason` stored and logged; request still returns 200 with the failure detail.

### 5.2 Retrieval (`hybrid_retrieve`)
1. **Dense** — embed query, Qdrant search top-20 filtered by `tenant_id`.
2. **BM25** — in-process `BM25Okapi` over the tenant's chunks; index cached per tenant and rebuilt when the tenant chunk count changes; top-20, positive scores only.
3. **Fusion** — Reciprocal Rank Fusion (`k=60`), union of candidates, records which retriever(s) hit each chunk.
4. **Rerank** — `BAAI/bge-reranker-base` cross-encoder scores `(query, chunk)` pairs; return top-5.
Each stage is a `timed_stage` event; empty fusion is flagged `no_results_from_either_retriever`.

### 5.3 Answer generation (`POST /chat`)
1. Auth + tenant check; resume or create a `conversation`.
2. `hybrid_retrieve`; if empty → return a canned "no relevant info" answer (`error_reason=empty_retrieval`).
3. Build a strict grounded prompt: numbered source excerpts with `(filename, page)`, system instruction to answer **only** from excerpts, cite `[N]`, and admit when excerpts are insufficient.
4. LLM call via Ollama (`stream=False`), retried 2×.
5. **Citation extraction** — regex `\[(\d+)\]`; each marker validated against the excerpt count → `valid_citations[{marker, document_id, filename, page_number, snippet}]`, `invalid_citation_markers`, and `citation_accuracy = valid / total_cited`.
6. Persist user + assistant messages (assistant message stores `citations` JSON).
7. Response includes answer, citations, invalid markers, citation accuracy, and retrieved-chunk previews.

### 5.4 Evaluation (offline, `app/eval/run_eval.py`)
- **Golden set** — `generate_golden_set.py` samples substantive chunks (`token_count > 80`) and prompts the LLM to write one answerable question per chunk, recording the expected `{document_id, page_number}`. Human review expected before use. `golden_set/qa.json` is checked in (Levine Academy employee-handbook corpus).
- **Per question:** run retrieval → `recall@k`, `MRR`, `hit` against gold `(doc_id, page)`; run generation → `citation_accuracy`; run **LLM-as-judge** (`llama3.2:3b`) → `faithfulness_score` (0–1) + `hallucination` bool; record retrieval / generation / total latency.
- **Aggregate:** means for retrieval + generation metrics, hallucination rate, failure rate, and p50/p95 latency (custom `percentile`). Rows persisted to `evaluation_results`; full JSON report written to `golden_set/eval_report_<run_id>.json`.

---

## 6. Multi-Tenancy & Security

- **Auth:** `POST /users` issues `ekp_<token_urlsafe(32)>`; only `sha256(salt + key)` is stored, raw key shown once. Requests carry `Authorization: Bearer <key>`; `get_current_user` resolves the user by hash.
- **Isolation:**
  - Vector search always applies a `tenant_id` `FieldCondition` filter.
  - BM25 corpus is built per tenant from tenant-filtered rows.
  - Relational queries filter on `tenant_id`; `require_tenant_match` rejects a key used against another tenant's `tenant_id` (403).
- **Blast radius:** a leaked key exposes exactly one tenant's corpus.

### Known gaps / hardening backlog
- `/tenants`, `/users`, and `GET /documents/{id}` are unauthenticated in v1 — should be admin-scoped; `GET /documents/{id}` also lacks a tenant check (IDOR on metadata).
- API-key hash is unsalted-per-key (single global salt) and fast (SHA-256) — acceptable for high-entropy random keys, but a per-key salt + constant-time compare is the standard.
- No rate limiting, request size caps beyond parser limits, or audit log of retrieval queries.
- Secrets (`JWT_SECRET`, `API_KEY_SALT`) default to placeholder values; deployment must override.
- Ingestion is synchronous — a large PDF blocks the worker; move to a task queue.

---

## 7. Observability

`app/core/logging.py` provides `StructuredLogger.event()` and a `timed_stage`
context manager. Every stage (`ingestion.parse`, `retrieval.dense`,
`generation.llm_call`, …) emits one JSON line to stdout **and** `ekp_events.log`
with `ts, stage, latency_ms, success, tenant_id, error_reason` plus stage-specific
fields (`n_chunks`, `n_results`, `prompt_length_chars`, …). This gives a
per-request latency breakdown and failure attribution without an APM dependency.
The eval harness is the offline complement — quality regression detection over time.

---

## 8. Deployment & CI/CD

- **Local:** `docker-compose.yml` brings up Postgres, Qdrant, and the app (hot-reload, `data/`, `app/`, `golden_set/` mounted); Ollama runs on the host via `host.docker.internal`.
- **Image:** `python:3.11-slim`, system deps for `psycopg2` + `sentence-transformers`, pinned `requirements.txt`.
- **CI (`.github/workflows/ci.yml`):** on push/PR to `main` — spin up Postgres + Qdrant services → `pytest app/tests/` → `docker build` → run container → poll `/health` for 30s → clean up.
- **Deploy (`.github/workflows/deploy.yml`):** on successful CI on `main`, a self-hosted runner executes `deploy_local.sh` (health check + rollback). *Note: `deploy_local.sh` is referenced but not yet in the repo — deployment script is a TODO.*

### Tests (`app/tests/`)
- `test_auth.py` — key format, uniqueness, hash determinism / irreversibility / length.
- `test_metrics.py` — recall@k / MRR / precision / percentile edge cases.
- `test_citations.py` — valid/invalid marker extraction, accuracy math.

Coverage is unit-level on pure logic; retrieval/generation/ingestion integration
paths rely on the eval harness and the CI smoke test rather than mocked unit tests.

---

## 9. Technology Choices & Rationale

| Choice | Why | Trade-off |
|---|---|---|
| **Hybrid dense + BM25 + RRF + rerank** | Dense handles paraphrase, BM25 handles exact terms / rare tokens (IDs, acronyms); RRF needs no score calibration; cross-encoder fixes ordering | Reranker adds latency + a model download; BM25 index is in-process (see §10) |
| **Qdrant** | Native payload filtering for tenant isolation, simple ops, on-prem | Another stateful service to run |
| **Ollama (local models)** | Data never leaves the box; zero per-token cost; model swap via env | Quality/latency below hosted frontier models; 8B gen model limits reasoning |
| **Postgres as source of truth** | Chunk metadata, conversations, eval results in one transactional store | Dual-write with Qdrant needs care on failure paths |
| **LLM-as-judge for faithfulness** | Scales faithfulness scoring without human labeling every run | Judge model noise; needs periodic human calibration |
| **`create_all` on startup + Alembic wired** | Fast iteration in v1, migration path ready | Must switch to migrations-only before real data |
| **Streamlit UI** | Fast to build; the Quality & Trust tab doubles as a stakeholder trust artifact | Not a production frontend |
| **Synchronous ingestion** | Simplest correct implementation; immediate status in the response | Blocks on large docs |

---

## 10. Scaling & Known Limitations

| Area | v1 behavior | Path forward |
|---|---|---|
| Ingestion throughput | Synchronous, per-chunk embedding calls | Background worker/queue (RQ/Celery/Arq); batch embedding endpoint |
| BM25 index | Rebuilt in-process per tenant on chunk-count change; lives in one worker's memory | Move to Postgres FTS or an OpenSearch/Elasticsearch index; or Qdrant sparse vectors |
| Multi-worker consistency | In-proc BM25 + reranker singletons don't share across workers | Externalize lexical search; dedicated rerank service |
| Reranker cold start | First request loads `bge-reranker-base` lazily | Warm on startup; pin in a model server |
| Conversation context | Stored but not fed back into the prompt | Add history window / query rewriting for follow-ups |
| Retrieval quality knobs | Fixed top-K (20/20/5), fixed chunk size | Per-tenant tuning; evaluate chunk size 256–1024; add metadata filters (source_category) |
| Doc lifecycle | No re-index / delete / version endpoints | CRUD on documents with Qdrant + Postgres cascade (ORM cascade already set) |
| Auth surface | Admin endpoints unauthenticated; IDOR on `GET /documents/{id}` | Admin role + tenant checks on all read paths |
| HA | Single node, single Postgres, single Qdrant | Managed Postgres, Qdrant cluster, N stateless app replicas behind an LB |

---

## 11. Repository Layout

```
app/
  main.py                 FastAPI app + endpoints
  core/                   config, db engine, ORM models, structured logging
  tenancy/auth.py         API-key auth + tenant guard
  ingestion/              parsers, chunker, embedder, indexer, pipeline
  retrieval/              dense, bm25, fusion, reranker, hybrid
  generation/             prompt, llm_client, citations, pipeline
  eval/                   golden-set gen, metrics, llm_judge, run_eval
  tests/                  auth, metrics, citations unit tests
frontend/streamlit_app.py Chat + Quality & Trust UI
golden_set/qa.json        checked-in evaluation set
db/migrations/            Alembic scaffold
.github/workflows/        ci.yml, deploy.yml
docker-compose.yml, Dockerfile, requirements.txt, .env.example
```

*(`ekp-project/` is an earlier scaffold of the same system, superseded by `app/`.)*

---

## 12. Build Phases (delivered)

0. Scaffolding, config, Docker, Postgres/Qdrant.
1–2. Tenancy + API-key auth.
3. Ingestion pipeline (parse/chunk/embed/index) with per-stage observability.
4–5. Hybrid retrieval + fusion + reranking; `/search` test endpoint.
6. RAG generation with grounded prompt + `/chat` + conversation persistence.
7. Citation extraction, validation, and accuracy.
8. Evaluation harness — golden set, retrieval metrics, LLM judge, latency report.
9. Streamlit UI with the Quality & Trust dashboard.
10. CI/CD — GitHub Actions test + build + smoke test, deploy workflow.
