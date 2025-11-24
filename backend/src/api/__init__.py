"""
API router configuration for Data Agent V4 Backend
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include sub-routers
# Example:
# from src.api.endpoints import auth, users, tenants
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])


@api_router.get("/info")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Data Agent V4 API",
        "version": "1.0.0",
        "status": "ready"
    }