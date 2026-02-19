"""
API v2 router package.
"""

from fastapi import APIRouter
from .endpoints import query_v2

api_router_v2 = APIRouter()
api_router_v2.include_router(query_v2.router, tags=["Query V2"])

__all__ = ["api_router_v2"]
