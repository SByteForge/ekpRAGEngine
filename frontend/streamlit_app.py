"""
EKP demo UI - Phase 9, updated with a Quality & Trust tab.

Two tabs:
  - Chat: talk to the RAG system, see citations per answer
  - Quality & Trust: real measured metrics from the eval harness, each with
    a plain-English definition so a non-technical viewer understands what
    the number means and why it should (or shouldn't) build confidence.

Run with: streamlit run frontend/streamlit_app.py
"""
import glob
import json
import os

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Enterprise Knowledge Platform", page_icon="📚", layout="wide")

# --- session state ---
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.api_key}"} if st.session_state.api_key else {}


# =========================================================================
# METRIC DEFINITIONS - plain English, shown as tooltips and in the
# expandable "what do these mean" section. Edit the wording here only.
# =========================================================================
METRIC_DEFINITIONS = {
    "recall_at_k": {
        "label": "Recall@K",
        "long": (
            "Out of every question we tested, how often did the search step actually "
            "find the correct source document in its results? 100% means the right "
            "document was found every single time - the system never missed it entirely."
        ),
    },
    "mrr": {
        "label": "MRR (Mean Reciprocal Rank)",
        "long": (
            "When the correct document WAS found, how close to the top of the results "
            "was it? A score of 1.0 means it was always the #1 result. A lower score "
            "(like 0.5) would mean the right answer was often buried further down, "
            "making it more likely to be missed or ignored."
        ),
    },
    "hit_rate": {
        "label": "Hit rate",
        "long": (
            "The percentage of test questions where at least one relevant source "
            "document was successfully retrieved. Closely related to Recall@K - "
            "think of this as the same idea expressed as a simple percentage."
        ),
    },
    "faithfulness_mean": {
        "label": "Faithfulness",
        "long": (
            "Checked by a second, independent AI acting as a fact-checker: does every "
            "claim in the generated answer actually appear in the source documents, or "
            "did the AI add information it wasn't given? Scored 0 to 1. A score near "
            "1.0 means the answer is fully grounded in real source material, not the "
            "AI's own assumptions or invented facts."
        ),
    },
    "hallucination_rate": {
        "label": "Hallucination rate",
        "long": (
            "The percentage of answers that included at least one fact NOT found "
            "anywhere in the source documents - i.e. the AI invented it. This is the "
            "single most important trust metric for a knowledge assistant: a low "
            "hallucination rate means you can rely on the answers being grounded in "
            "your real documents rather than the model's general training data."
        ),
    },
    "citation_accuracy_mean": {
        "label": "Citation accuracy",
        "long": (
            "When the AI cites a source like [1] or [2] in its answer, this checks "
            "whether that citation actually corresponds to a real document the system "
            "retrieved - not a citation the AI made up. 100% means every citation in "
            "every answer was independently verified to point to a real, correct source."
        ),
    },
    "failure_rate": {
        "label": "Failure rate",
        "long": (
            "The percentage of questions where something in the pipeline failed "
            "outright - search came back empty, the AI model timed out, or another "
            "error occurred - so no answer was produced at all. 0% means the system "
            "successfully answered every question it was tested on."
        ),
    },
}


def metric_help(key: str) -> str:
    return METRIC_DEFINITIONS.get(key, {}).get("long", "")


def format_pct(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def load_latest_eval_report():
    """Finds the most recently written eval_report_*.json in golden_set/."""
    candidates = glob.glob("golden_set/eval_report_*.json")
    if not candidates:
        return None
    latest = max(candidates, key=os.path.getmtime)
    with open(latest) as f:
        return json.load(f), latest


# =========================================================================
# SIDEBAR - tenant + auth + document upload (unchanged from Phase 9)
# =========================================================================
with st.sidebar:
    st.header("Setup")

    if not st.session_state.tenant_id:
        st.subheader("1. Tenant")
        mode = st.radio("Tenant", ["Create new", "Use existing"], label_visibility="collapsed")

        if mode == "Create new":
            tenant_name = st.text_input("Tenant name", placeholder="acme")
            if st.button("Create tenant") and tenant_name:
                try:
                    resp = requests.post(f"{API_BASE}/tenants", data={"name": tenant_name}, timeout=10)
                    resp.raise_for_status()
                    st.session_state.tenant_id = resp.json()["id"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create tenant: {e}")
        else:
            existing_id = st.text_input("Tenant UUID", placeholder="19aee8b0-...")
            if st.button("Use this tenant") and existing_id:
                st.session_state.tenant_id = existing_id
                st.rerun()

    else:
        st.success(f"Tenant: `{st.session_state.tenant_id[:8]}...`")
        if st.button("Switch tenant"):
            st.session_state.tenant_id = None
            st.session_state.api_key = None
            st.rerun()

        if not st.session_state.api_key:
            st.subheader("2. Auth")
            auth_mode = st.radio("Auth", ["Create new key", "Use existing key"], label_visibility="collapsed")

            if auth_mode == "Create new key":
                email = st.text_input("Email", placeholder="you@example.com")
                if st.button("Create API key") and email:
                    try:
                        resp = requests.post(
                            f"{API_BASE}/users",
                            data={"tenant_id": st.session_state.tenant_id, "email": email},
                            timeout=10,
                        )
                        resp.raise_for_status()
                        st.session_state.api_key = resp.json()["api_key"]
                        st.rerun()
                    except requests.exceptions.HTTPError as e:
                        st.error(f"Failed: {e.response.json().get('detail', str(e))}")
                    except Exception as e:
                        st.error(f"Failed to create user: {e}")
            else:
                existing_key = st.text_input("API key", type="password", placeholder="ekp_...")
                if st.button("Use this key") and existing_key:
                    st.session_state.api_key = existing_key
                    st.rerun()
        else:
            st.success("Authenticated")
            if st.button("Log out"):
                st.session_state.api_key = None
                st.rerun()

    if st.session_state.tenant_id and st.session_state.api_key:
        st.divider()
        st.subheader("Upload document")
        uploaded_file = st.file_uploader("PDF, Markdown, or DOCX", type=["pdf", "md", "markdown", "docx"])
        source_category = st.selectbox("Category", ["engineering", "healthcare", "hr", "other"])
        if uploaded_file and st.button("Ingest document"):
            with st.spinner("Parsing → chunking → embedding → indexing..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    data = {"tenant_id": st.session_state.tenant_id, "source_category": source_category}
                    resp = requests.post(
                        f"{API_BASE}/documents/ingest",
                        headers=auth_headers(),
                        data=data,
                        files=files,
                        timeout=300,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    if result["status"] == "indexed":
                        st.success(f"Indexed {result['n_chunks']} chunks from {uploaded_file.name}")
                    else:
                        st.error(f"Ingestion failed: {result['error_reason']}")
                except requests.exceptions.HTTPError as e:
                    st.error(f"Failed: {e.response.json().get('detail', str(e))}")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

# =========================================================================
# MAIN AREA - tabbed: Chat | Quality & Trust
# =========================================================================
st.title("📚 Enterprise Knowledge Platform")

tab_chat, tab_quality = st.tabs(["💬 Chat", "✅ Quality & Trust"])

# --- CHAT TAB ---
with tab_chat:
    st.caption("Ask questions about your indexed documents. Answers are grounded with citations.")

    if not st.session_state.tenant_id or not st.session_state.api_key:
        st.info("Set up a tenant and API key in the sidebar to get started.")
    else:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("citations"):
                    with st.expander(f"📎 {len(msg['citations'])} source(s)"):
                        for c in msg["citations"]:
                            st.markdown(f"**[{c['marker']}] {c['filename']}**, page {c['page_number']}")
                            st.caption(c["snippet"])

        question = st.chat_input("Ask a question about your documents...")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Retrieving → generating → citing... (can take 15-30s on local CPU inference)"):
                    try:
                        data = {"tenant_id": st.session_state.tenant_id, "question": question}
                        if st.session_state.conversation_id:
                            data["conversation_id"] = st.session_state.conversation_id

                        resp = requests.post(
                            f"{API_BASE}/chat", headers=auth_headers(), data=data, timeout=120
                        )
                        resp.raise_for_status()
                        result = resp.json()

                        st.session_state.conversation_id = result["conversation_id"]
                        st.write(result["answer"])

                        # Per-answer trust signal - computed, not a vibe
                        if result["citation_accuracy"] is not None:
                            acc = result["citation_accuracy"]
                            if acc == 1.0:
                                st.success(
                                    f"✓ All citations verified against real sources ({len(result['citations'])} source(s))"
                                )
                            else:
                                st.warning(
                                    f"⚠ Citation accuracy {format_pct(acc)} - some citations could not be verified"
                                )

                        if result["citations"]:
                            with st.expander(f"📎 {len(result['citations'])} source(s)"):
                                for c in result["citations"]:
                                    st.markdown(f"**[{c['marker']}] {c['filename']}**, page {c['page_number']}")
                                    st.caption(c["snippet"])

                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": result["answer"], "citations": result["citations"]}
                        )

                    except requests.exceptions.HTTPError as e:
                        error_detail = e.response.json().get("detail", str(e))
                        st.error(f"Request failed: {error_detail}")
                    except Exception as e:
                        st.error(f"Something went wrong: {e}")

# --- QUALITY & TRUST TAB ---
with tab_quality:
    st.caption(
        "These numbers come from running the system against a test set of real questions "
        "with known-correct answers, then measuring exactly how it performed - not estimates."
    )

    report_data = load_latest_eval_report()

    if report_data is None:
        st.info(
            "No eval report found yet. Run the evaluation harness first:\n\n"
            "```\npython -m app.eval.run_eval --tenant-id <your-tenant-id>\n```"
        )
    else:
        report, report_path = report_data
        summary = report["summary"]

        st.caption(f"Source: `{report_path}` · Run ID `{summary['run_id']}` · {summary['n_total']} test questions")

        st.subheader("Search quality")
        st.caption("Can the system find the right information in your documents?")
        c1, c2, c3 = st.columns(3)
        c1.metric(
            METRIC_DEFINITIONS["recall_at_k"]["label"],
            format_pct(summary["retrieval"]["recall_at_k_mean"]),
            help=metric_help("recall_at_k"),
        )
        c2.metric(
            METRIC_DEFINITIONS["mrr"]["label"],
            f"{summary['retrieval']['mrr_mean']:.2f}" if summary["retrieval"]["mrr_mean"] is not None else "N/A",
            help=metric_help("mrr"),
        )
        c3.metric(
            METRIC_DEFINITIONS["hit_rate"]["label"],
            format_pct(summary["retrieval"]["hit_rate"]),
            help=metric_help("hit_rate"),
        )

        st.subheader("Answer quality")
        st.caption("When the system answers, can you trust what it says?")
        c1, c2, c3 = st.columns(3)
        c1.metric(
            METRIC_DEFINITIONS["faithfulness_mean"]["label"],
            format_pct(summary["generation"]["faithfulness_mean"]),
            help=metric_help("faithfulness_mean"),
        )
        c2.metric(
            METRIC_DEFINITIONS["hallucination_rate"]["label"],
            format_pct(summary["generation"]["hallucination_rate"]),
            help=metric_help("hallucination_rate"),
        )
        c3.metric(
            METRIC_DEFINITIONS["citation_accuracy_mean"]["label"],
            format_pct(summary["generation"]["citation_accuracy_mean"]),
            help=metric_help("citation_accuracy_mean"),
        )

        st.subheader("System reliability")
        st.caption("How dependable is the system, and how fast is it?")
        c1, c2 = st.columns(2)
        c1.metric(
            METRIC_DEFINITIONS["failure_rate"]["label"],
            format_pct(summary["failure_rate"]),
            help=metric_help("failure_rate"),
        )
        c2.metric(
            "Questions tested",
            f"{summary['n_success']}/{summary['n_total']}",
            help="How many test questions were run, and how many completed successfully end to end.",
        )

        st.markdown("**Response time** (seconds)")
        lat = summary["latency_ms"]
        lc1, lc2, lc3 = st.columns(3)
        lc1.metric(
            "Search — typical / slowest 5%",
            f"{lat['retrieval_p50']/1000:.1f}s / {lat['retrieval_p95']/1000:.1f}s",
            help=(
                "Time to search and find relevant source documents for a question. "
                "'Typical' (P50) is the middle case; 'slowest 5%' (P95) shows worst-case "
                "waits, which matters more for user experience than the average."
            ),
        )
        lc2.metric(
            "Answer writing — typical / slowest 5%",
            f"{lat['generation_p50']/1000:.1f}s / {lat['generation_p95']/1000:.1f}s",
            help="Time for the AI model to read the sources and write an answer.",
        )
        lc3.metric(
            "Total — typical / slowest 5%",
            f"{lat['total_p50']/1000:.1f}s / {lat['total_p95']/1000:.1f}s",
            help="Total time from question asked to answer delivered.",
        )

        with st.expander("📖 What do all these metrics mean? (plain English)"):
            st.markdown("#### Search quality")
            for key in ["recall_at_k", "mrr", "hit_rate"]:
                d = METRIC_DEFINITIONS[key]
                st.markdown(f"**{d['label']}** — {d['long']}")
            st.markdown("#### Answer quality")
            for key in ["faithfulness_mean", "hallucination_rate", "citation_accuracy_mean"]:
                d = METRIC_DEFINITIONS[key]
                st.markdown(f"**{d['label']}** — {d['long']}")
            st.markdown("#### System reliability")
            d = METRIC_DEFINITIONS["failure_rate"]
            st.markdown(f"**{d['label']}** — {d['long']}")
            st.markdown(
                "**Response time (P50/P95)** — P50 is the *typical* wait: half of all "
                "questions were answered faster than this, half slower. P95 is closer to "
                "worst-case: only 5% of questions took longer than this. Both matter - P50 "
                "tells you the normal experience, P95 tells you how bad it gets sometimes."
            )

        with st.expander("🔍 Per-question results"):
            for r in report["results"]:
                icon = "✅" if r["success"] else "❌"
                st.markdown(f"{icon} **{r['question']}**")
                if r["success"]:
                    st.caption(
                        f"Hit: {r['hit']} · Faithfulness: {format_pct(r['faithfulness_score'])} · "
                        f"Citation accuracy: {format_pct(r['citation_accuracy'])} · "
                        f"Retrieval: {r['retrieval_latency_ms']:.0f}ms · Generation: {r['generation_latency_ms']:.0f}ms"
                    )
                else:
                    st.caption(f"Failed: {r['error_reason']}")
                st.divider()