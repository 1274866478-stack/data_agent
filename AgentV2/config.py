"""
# [CONFIG] Agent配置管理模块

## [HEADER]
**文件名**: config.py
**职责**: SQL Agent的配置管理 - 加载环境变量、支持独立模式和Backend集成模式、配置验证
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Agent配置管理

## [INPUT]
### Config类初始化参数
- **deepseek_api_key: str** - DeepSeek API密钥（默认从环境变量或Backend配置）
- **deepseek_base_url: str** - DeepSeek API基础URL（默认"https://api.deepseek.com"）
- **deepseek_model: str** - DeepSeek模型名称（默认"deepseek-chat"）
- **database_url: str** - PostgreSQL数据库连接URL（默认从环境变量或Backend配置）

### 配置加载优先级
1. Backend配置（lazy load，如果可用）
2. 环境变量（.env文件或系统环境变量）
3. 默认值

## [OUTPUT]
### Config类属性
- **deepseek_api_key: str** - DeepSeek API密钥
- **deepseek_base_url: str** - DeepSeek API基础URL
- **deepseek_model: str** - DeepSeek模型名称
- **database_url: str** - PostgreSQL数据库连接URL

### Config类方法
- **validate_config()**: bool - 验证配置是否完整
  - **Raises**: ValueError（如果deepseek_api_key或database_url缺失）
- **__init__(**data)**: 初始化配置（优先使用Backend配置，回退到环境变量）

### 全局实例
- **config**: Config - 全局配置实例（模块级别）

## [LINK]
**上游依赖** (已读取源码):
- [pydantic](https://docs.pydantic.dev/) - Pydantic数据验证库（BaseModel）
- [python-dotenv](https://github.com/theskumar/python-dotenv) - 环境变量加载（load_dotenv）
- [python-pathlib](https://docs.python.org/3/library/pathlib.html) - 路径处理（Path）
- [backend/src/app/core/config.py](../backend/src/app/core/config.py) - Backend配置（get_settings，lazy load）

**下游依赖** (已读取源码):
- [./sql_agent.py](./sql_agent.py) - Agent主程序（使用config对象）
- [./run.py](./run.py) - 启动脚本（调用config.validate_config）

**调用方**:
- **sql_agent.py**: 导入config对象获取DeepSeek API和数据库配置
- **run.py**: 调用config.validate_config()验证配置

## [POS]
**路径**: Agent/config.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 2 层（pydantic, python-dotenv）
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

