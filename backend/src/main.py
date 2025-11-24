"""
Data Agent V4 Backend Application
FastAPI-based multi-tenant SaaS platform backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import settings
from src.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Data Agent V4 Backend is starting up...")
    yield
    # Shutdown
    print("🛑 Data Agent V4 Backend is shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant SaaS Platform for Intelligent Data Analysis",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {
        "message": "Data Agent V4 Backend API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "data-agent-v4-backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )