"""
API v1 router for Data Agent V4 Backend
"""

from fastapi import APIRouter
from .endpoints import rag_sql

# Create API v1 router
api_router = APIRouter()

# Include RAG-SQL endpoints
api_router.include_router(
    rag_sql.router,
    prefix="/rag-sql",
    tags=["RAG-SQL"]
)

# TODO: Add other endpoint routers here
# api_router.include_router(health.router, prefix="/health", tags=["Health"])
# api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
# api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
# api_router.include_router(llm.router, prefix="/llm", tags=["LLM"])