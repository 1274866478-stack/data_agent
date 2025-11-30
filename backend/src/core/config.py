"""
Configuration settings for Data Agent V4 Backend
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "Data Agent V4 Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Security settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dataagent_v4"
    DATABASE_SYNC_URL: str = "postgresql://user:password@localhost/dataagent_v4"

    # CORS settings
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Environment
    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: str = "INFO"

    # MinIO settings
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "dataagent-files"
    MINIO_ROOT_USER: Optional[str] = None
    MINIO_ROOT_PASSWORD: Optional[str] = None

    # ChromaDB settings
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ZhipuAI settings
    ZHIPUAI_API_KEY: str = ""
    ZHIPUAI_DEFAULT_MODEL: str = "glm-4.6"
    ZHIPUAI_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    ZHIPUAI_TIMEOUT: int = 30
    ZHIPUAI_MAX_RETRIES: int = 3

    # Clerk settings
    CLERK_JWT_PUBLIC_KEY: Optional[str] = None
    CLERK_API_URL: str = "https://api.clerk.dev"

    # CORS origins
    CORS_ORIGINS: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings