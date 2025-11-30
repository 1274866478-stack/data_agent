"""
应用配置管理模块
处理环境变量读取、配置验证和应用设置
"""

from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置类"""

    # 应用基础配置
    app_name: str = "Data Agent Backend"
    app_version: str = "1.0.0"
    environment: str = "development"  # development, testing, production
    debug: bool = False

    # 数据库配置
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    database_connect_timeout: int = 10

    # MinIO 配置
    minio_endpoint: str = "minio:9000"
    minio_access_key: str  # 必须通过环境变量设置，无默认值以确保安全
    minio_secret_key: str  # 必须通过环境变量设置，无默认值以确保安全
    minio_secure: bool = False

    # ChromaDB 配置
    chroma_host: str = "vector_db"
    chroma_port: int = 8000
    chroma_collection_name: str = "knowledge_base"

    # Redis 缓存配置
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    redis_max_connections: int = 10
    redis_timeout: int = 5
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    cache_type: str = "memory"  # memory, redis

    # 智谱 AI 配置
    zhipuai_api_key: str
    zhipuai_default_model: str = "glm-4.6"
    zhipuai_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipuai_timeout: int = 30
    zhipuai_max_retries: int = 3

    # OpenRouter 配置
    openrouter_api_key: Optional[str] = None
    openrouter_default_model: str = "google/gemini-2.0-flash-exp"
    openrouter_referer: Optional[str] = None  # 可选，用于OpenRouter排名
    openrouter_app_name: str = "Data Agent"  # 可选，用于OpenRouter排名

    # Clerk 认证配置
    clerk_jwt_public_key: Optional[str] = None  # Clerk JWT公钥（开发环境可选）
    clerk_domain: str = "clerk.accounts.dev"  # Clerk域名（开发环境）
    clerk_api_key: Optional[str] = None  # Clerk API密钥（可选，用于高级功能）
    clerk_secret_key: Optional[str] = None  # Clerk Secret Key（可选）
    clerk_webhook_secret: Optional[str] = None  # Clerk Webhook Secret（可选）

    # API 配置
    api_v1_prefix: str = "/api/v1"
    api_key: Optional[str] = None  # API密钥，如果设置则所有API需要认证

    # 密钥轮换配置
    key_rotation_enabled: bool = True
    key_rotation_reminder_days: int = 7  # 提前7天提醒
    key_rotation_interval_days: int = 90  # 90天轮换周期

    # Sentry 监控配置
    sentry_dsn: Optional[str] = None  # Sentry项目DSN
    sentry_environment: Optional[str] = None  # Sentry环境名称,默认使用environment
    sentry_traces_sample_rate: float = 0.1  # 性能追踪采样率 (0.0-1.0)

    @validator("database_url")
    def validate_database_url(cls, v):
        """验证数据库连接字符串格式"""
        # 允许PostgreSQL和SQLite（用于测试）
        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "sqlite://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL or SQLite connection string")
        return v



    @validator("clerk_jwt_public_key")
    def validate_clerk_jwt_public_key(cls, v, values):
        """验证Clerk JWT公钥"""
        # 在开发环境中允许为空
        environment = values.get('environment', 'development')
        if environment == 'development' and v is None:
            return v
        # 在测试环境中允许测试密钥
        if environment in ('testing',) and v in ('test_public_key_placeholder', 'test_key'):
            return v
        if not v or not v.startswith(('-----BEGIN PUBLIC KEY-----', 'ssh-rsa')):
            raise ValueError("CLERK_JWT_PUBLIC_KEY must be a valid PEM format public key")
        return v

    @validator("minio_access_key")
    def validate_minio_access_key(cls, v, values):
        """验证MinIO访问密钥，禁止使用默认值和弱密钥"""
        # 测试环境允许测试密钥
        environment = values.get('environment', 'development')
        if environment in ('testing',) and v.startswith('test_'):
            return v

        # 开发环境暂时允许较短的密钥进行测试
        if environment == 'development':
            if v == "minioadmin":
                raise ValueError(
                    'MINIO_ACCESS_KEY cannot use default value "minioadmin". '
                    "Please set a strong access key via environment variable."
                )
            if len(v) < 8:  # 开发环境暂时降低要求
                raise ValueError(
                    "MINIO_ACCESS_KEY must be at least 8 characters long for development. "
                    "Use 'python scripts/generate_keys.py' to generate a strong key."
                )
            return v

        if v == "minioadmin":
            raise ValueError(
                'MINIO_ACCESS_KEY cannot use default value "minioadmin". '
                "Please set a strong access key via environment variable."
            )
        if len(v) < 16:
            raise ValueError(
                "MINIO_ACCESS_KEY must be at least 16 characters long for security. "
                "Use 'python scripts/generate_keys.py' to generate a strong key."
            )

        # 检查弱密码模式（生产和开发环境）
        weak_patterns = ["password", "admin", "demo", "default", "changeme"]
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                f"MINIO_ACCESS_KEY contains weak password pattern. "
                "Use 'python scripts/generate_keys.py' to generate a strong key."
            )

        return v

    @validator("zhipuai_api_key")
    def validate_zhipuai_api_key(cls, v, values):
        """验证智谱AI API密钥"""
        environment = values.get('environment', 'development')

        # 测试环境允许测试密钥
        if environment in ('testing',) and v.startswith('test_'):
            return v

        # 开发环境允许占位符，但记录警告
        if environment == 'development' and v in ('dev_placeholder', 'test_key'):
            return v

        # 检查智谱AI API密钥格式（通常以特定的前缀开头）
        if not v or len(v) < 40:
            raise ValueError(
                "ZHIPUAI_API_KEY must be at least 40 characters long. "
                "Please get a valid API key from https://open.bigmodel.cn/"
            )

        # 检查弱密钥模式 - 增强安全检查
        weak_patterns = [
            "example", "demo", "test", "placeholder", "fake", "123456",
            "password", "secret", "key", "token", "sample", "default"
        ]
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                f"ZHIPUAI_API_KEY contains weak pattern: '{pattern}'. "
                "Please use a valid API key from https://open.bigmodel.cn/"
            )

        # 检查重复字符模式（弱密钥特征）
        if len(set(v)) < len(v) * 0.3:  # 如果唯一字符少于30%
            raise ValueError(
                "ZHIPUAI_API_KEY appears to be weak (low character variety). "
                "Please use a proper API key from https://open.bigmodel.cn/"
            )

        return v

    @validator("minio_secret_key")
    def validate_minio_secret_key(cls, v, values):
        """验证MinIO秘密密钥，禁止使用默认值和弱密钥"""
        # 测试环境允许测试密钥
        environment = values.get('environment', 'development')
        if environment in ('testing',) and v.startswith('test_'):
            return v

        # 开发环境暂时允许较短的密钥进行测试
        if environment == 'development':
            if v == "minioadmin":
                raise ValueError(
                    'MINIO_SECRET_KEY cannot use default value "minioadmin". '
                    "Please set a strong secret key via environment variable."
                )
            if len(v) < 16:  # 开发环境暂时降低要求
                raise ValueError(
                    "MINIO_SECRET_KEY must be at least 16 characters long for development. "
                    "Use 'python scripts/generate_keys.py' to generate a strong key."
                )
            return v

        if v == "minioadmin":
            raise ValueError(
                'MINIO_SECRET_KEY cannot use default value "minioadmin". '
                "Please set a strong secret key via environment variable."
            )
        if len(v) < 32:
            raise ValueError(
                "MINIO_SECRET_KEY must be at least 32 characters long for security. "
                "Use 'python scripts/generate_keys.py' to generate a strong key."
            )

        # 检查弱密码模式（生产和开发环境）
        weak_patterns = ["password", "admin", "demo", "default", "changeme"]
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                f"MINIO_SECRET_KEY contains weak password pattern. "
                "Use 'python scripts/generate_keys.py' to generate a strong key."
            )

        return v

    @validator("openrouter_api_key")
    def validate_openrouter_api_key(cls, v, values):
        """验证OpenRouter API密钥"""
        if not v:  # OpenRouter是可选的
            return v

        environment = values.get('environment', 'development')

        # 测试环境允许测试密钥
        if environment in ('testing',) and v.startswith('test_'):
            return v

        # 开发环境允许占位符，但记录警告
        if environment == 'development' and v in ('dev_placeholder', 'test_key'):
            return v

        # 检查OpenRouter API密钥格式
        if len(v) < 20:
            raise ValueError(
                "OPENROUTER_API_KEY must be at least 20 characters long. "
                "Please get a valid API key from https://openrouter.ai/"
            )

        # 检查弱密钥模式
        weak_patterns = [
            "example", "demo", "test", "placeholder", "fake", "123456",
            "password", "secret", "key", "token", "sample", "default"
        ]
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                f"OPENROUTER_API_KEY contains weak pattern. "
                "Please use a valid API key from https://openrouter.ai/"
            )

        return v

    @validator("sentry_dsn")
    def validate_sentry_dsn(cls, v):
        """验证Sentry DSN格式"""
        if not v:  # Sentry是可选的
            return v

        if not v.startswith('https://'):
            raise ValueError(
                "SENTRY_DSN must start with 'https://'. "
                "Get a valid DSN from your Sentry project settings."
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的环境变量


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取应用设置实例

    Returns:
        Settings: 应用设置单例对象
    """
    return settings
