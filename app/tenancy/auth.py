import hashlib
import secrets
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db
from app.core.db_models import User


def generate_api_key() -> str:
    return f"ekp_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    salted = f"{settings.api_key_salt}{raw_key}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header. Expected: 'Bearer <api_key>'")
    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key:
        raise HTTPException(status_code=401, detail="Empty API key")
    hashed = hash_api_key(raw_key)
    user = db.query(User).filter(User.hashed_api_key == hashed).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


def require_tenant_match(user: User, requested_tenant_id: str):
    if user.tenant_id != requested_tenant_id:
        raise HTTPException(status_code=403, detail="API key does not belong to the requested tenant_id")
