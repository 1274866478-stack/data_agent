"""
Configuration module for SQL Agent
Loads environment variables and provides configuration settings
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    """Configuration settings for the SQL Agent"""
    
    # DeepSeek API settings
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/dataagent")
    
    def validate_config(self) -> bool:
        """Validate that all required configuration is present"""
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        return True


# Global config instance
config = Config()

