from fastapi import Request, HTTPException
from app.core.config import settings

async def tenant_scoping_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID is required")
    
    # Here you can add logic to validate the tenant_id against your database or other sources
    
    response = await call_next(request)
    return response