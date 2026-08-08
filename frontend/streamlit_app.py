"""
Minimal demo UI for the EKP - Phase 9. Talks to the real FastAPI backend
over HTTP, no mocking. Deliberately thin: this exists to give a live,
clickable demo surface, not to be a production frontend (that's Phase 9's
whole point per docs/ARCHITECTURE.md - v1 scope is "just enough to show a
live query with citations on screen").

Run with: streamlit run frontend/streamlit_app.py
"""
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
    st.session_state.chat_history = []  # list of {role, content, citations}


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.api_key}"} if st.session_state.api_key else {}


# --- sidebar: tenant + auth setup ---
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

# --- main: chat interface ---
st.title("📚 Enterprise Knowledge Platform")
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
                    data = {
                        "tenant_id": st.session_state.tenant_id,
                        "question": question,
                    }
                    if st.session_state.conversation_id:
                        data["conversation_id"] = st.session_state.conversation_id

                    resp = requests.post(
                        f"{API_BASE}/chat", headers=auth_headers(), data=data, timeout=120
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    st.session_state.conversation_id = result["conversation_id"]
                    st.write(result["answer"])

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