import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db, engine, Base
from app.core import db_models  # noqa: F401
from app.core.db_models import Document, Tenant, Conversation, Message, User
from app.ingestion.pipeline import ingest_document
from app.retrieval.hybrid import hybrid_retrieve
from app.generation.pipeline import answer_question
 
from app.tenancy.auth import generate_api_key, hash_api_key, get_current_user, require_tenant_match

app = FastAPI(title="Enterprise Knowledge Platform", version="0.1.0")
UPLOAD_DIR = Path("data/corpus")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
 
 
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
 
 
@app.post("/tenants")
def create_tenant(name: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(Tenant).filter(Tenant.name == name).first()
    if existing:
        return {"id": existing.id, "name": existing.name, "existed": True}
    tenant = Tenant(name=name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name, "existed": False}


@app.post("/users")
def create_user(tenant_id: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    """Issues a new API key. Raw key shown only once, only the hash is stored."""
    target_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not target_tenant:
        raise HTTPException(status_code=404, detail="Unknown tenant_id")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    raw_key = generate_api_key()
    user = User(tenant_id=tenant_id, email=email, hashed_api_key=hash_api_key(raw_key))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user_id": user.id, "tenant_id": user.tenant_id, "email": user.email,
        "api_key": raw_key, "warning": "Save this key now - it will not be shown again.",
    }
 
 
@app.post("/documents/ingest")
async def ingest(tenant_id: str = Form(...), source_category: str = Form(None),
                  file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_tenant_match(current_user, tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Unknown tenant_id")
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".md", ".markdown", ".docx"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}' in v1")
    tenant_dir = UPLOAD_DIR / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    dest_path = tenant_dir / file.filename
    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    document = Document(tenant_id=tenant_id, filename=file.filename, doc_type=ext.lstrip("."),
                         source_category=source_category, status="pending")
    db.add(document)
    db.commit()
    db.refresh(document)
    document = ingest_document(db, document, dest_path)
    return {"document_id": document.id, "status": document.status,
            "n_chunks": document.n_chunks, "error_reason": document.error_reason}
 
 
@app.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": doc.id, "filename": doc.filename, "status": doc.status,
            "n_chunks": doc.n_chunks, "error_reason": doc.error_reason}

@app.post("/search")
def search(tenant_id: str = Form(...), query: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Standalone retrieval test endpoint - Phase 5."""
    require_tenant_match(current_user, tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Unknown tenant_id")
    results = hybrid_retrieve(db, query=query, tenant_id=tenant_id)
    return {
        "query": query,
        "n_results": len(results),
        "results": [
            {"text": r.text[:500], "score": round(r.score, 4), "retriever": r.retriever,
             "filename": r.filename, "page_number": r.page_number, "document_id": r.document_id}
            for r in results
        ],
    }

@app.post("/chat")
def chat(tenant_id: str = Form(...), question: str = Form(...),
         conversation_id: str = Form(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Full RAG endpoint - Phase 6."""
    require_tenant_match(current_user, tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Unknown tenant_id")

    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Unknown conversation_id")
    else:
        conversation = Conversation(tenant_id=tenant_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    result = answer_question(db, question=question, tenant_id=tenant_id)

    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    db.add(Message(conversation_id=conversation.id, role="assistant",
                    content=result["answer"], citations=result["citations"]))
    db.commit()

    return {
        "conversation_id": conversation.id,
        "answer": result["answer"],
        "citations": result["citations"],
        "invalid_citation_markers": result["invalid_citation_markers"],
        "citation_accuracy": result["citation_accuracy"],
        "retrieved_chunks": result["retrieved_chunks"],
    }
