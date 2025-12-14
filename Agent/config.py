"""
Configuration module for SQL Agent
Loads environment variables and provides configuration settings
Supports both standalone mode and backend integration mode
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Backend config will be loaded lazily when needed
# This avoids circular dependency issues when Agent runs standalone
def _get_backend_config():
    """Lazily load backend config only when needed"""
    try:
        backend_src = Path(__file__).parent.parent / "backend" / "src"
        if backend_src.exists() and str(backend_src) not in sys.path:
            sys.path.insert(0, str(backend_src))
        
        from app.core.config import get_settings
        return get_settings()
    except (ImportError, ModuleNotFoundError, Exception):
        # Backend config not available, use standalone mode
        return None


class Config(BaseModel):
    """Configuration settings for the SQL Agent"""
    
    # DeepSeek API settings
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    
    # Database settings
    database_url: str = ""
    
    def __init__(self, **data):
        """Initialize config, preferring backend config if available"""
        # Try to use backend config first (lazy load)
        _backend_config = _get_backend_config()
        if _backend_config:
            try:
                data.setdefault("deepseek_api_key", getattr(_backend_config, "deepseek_api_key", "") or os.getenv("DEEPSEEK_API_KEY", ""))
                data.setdefault("deepseek_base_url", getattr(_backend_config, "deepseek_base_url", "https://api.deepseek.com") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
                data.setdefault("deepseek_model", getattr(_backend_config, "deepseek_default_model", "deepseek-chat") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
                data.setdefault("database_url", getattr(_backend_config, "database_url", "") or os.getenv("DATABASE_URL", ""))
            except Exception:
                # If backend config access fails, fall back to env vars
                pass
        
        # Standalone mode: use environment variables (fallback or default)
        if "deepseek_api_key" not in data:
            data.setdefault("deepseek_api_key", os.getenv("DEEPSEEK_API_KEY", ""))
        if "deepseek_base_url" not in data:
            data.setdefault("deepseek_base_url", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        if "deepseek_model" not in data:
            data.setdefault("deepseek_model", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        if "database_url" not in data:
            data.setdefault("database_url", os.getenv("DATABASE_URL", ""))
        
        super().__init__(**data)
    
    def validate_config(self) -> bool:
        """Validate that all required configuration is present"""
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        return True


# Global config instance
config = Config()

