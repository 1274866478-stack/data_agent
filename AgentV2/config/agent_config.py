# -*- coding: utf-8 -*-
"""
Agent Configuration - Agent 配置系统
====================================

统一管理 Agent V2 的所有配置项。

核心功能:
    - LLM 模型配置
    - 数据库连接配置
    - MCP 服务器配置
    - 中间件配置

作者: BMad Master
版本: 2.0.0
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


# ============================================================================
# 配置类
# ============================================================================

@dataclass
class LLMConfig:
    """LLM 模型配置"""
    model: str = "glm-4-flash"  # 🔧 改用智谱 GLM API（无内容审查问题）
    temperature: float = 0.1
    max_tokens: int = 2000
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        # 优先使用智谱 API（无内容审查问题）
        if "glm" in self.model.lower() or "zhipuai" in self.model.lower():
            if self.api_key is None:
                self.api_key = os.environ.get("ZHIPUAI_API_KEY", "")
            if self.base_url is None:
                self.base_url = os.environ.get("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        else:
            # DeepSeek 或其他 OpenAI 兼容 API
            if self.api_key is None:
                self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if self.base_url is None:
                self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = ""
    db_type: str = "postgresql"
    pool_size: int = 5
    max_overflow: int = 10

    def __post_init__(self):
        """初始化后处理"""
        if not self.url:
            self.url = os.environ.get(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/data_agent"
            )


@dataclass
class MCPConfig:
    """MCP 服务器配置"""
    enable_postgres: bool = True
    enable_echarts: bool = True
    postgres_command: str = "npx"
    postgres_args: List[str] = field(default_factory=lambda: ["@modelcontextprotocol/server-postgres"])
    echarts_command: str = "npx"
    echarts_args: List[str] = field(default_factory=lambda: ["@modelcontextprotocol/server-echarts"])


@dataclass
class MiddlewareConfig:
    """中间件配置"""
    enable_filesystem: bool = True
    enable_subagents: bool = True
    enable_skills: bool = True
    enable_sql_security: bool = True
    enable_tenant_isolation: bool = True
    enable_xai_logging: bool = False


@dataclass
class AgentConfig:
    """
    Agent V2 主配置类

    包含所有子配置：
    - llm: LLM 模型配置
    - database: 数据库配置
    - mcp: MCP 服务器配置
    - middleware: 中间件配置
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    middleware: MiddlewareConfig = field(default_factory=MiddlewareConfig)

    # 租户配置
    default_tenant_id: str = "default_tenant"

    # 图表配置
    chart_output_dir: str = "./charts"

    # 调试配置
    debug_mode: bool = False
    log_level: str = "INFO"


# ============================================================================
# 配置加载
# ============================================================================

def load_config_from_env() -> AgentConfig:
    """
    从环境变量加载配置

    Returns:
        AgentConfig 实例
    """
    config = AgentConfig()

    # LLM 配置
    if model := os.environ.get("LLM_MODEL"):
        config.llm.model = model
    if temp := os.environ.get("LLM_TEMPERATURE"):
        config.llm.temperature = float(temp)

    # 数据库配置
    if db_url := os.environ.get("DATABASE_URL"):
        config.database.url = db_url

    # 租户配置
    if tenant_id := os.environ.get("DEFAULT_TENANT_ID"):
        config.default_tenant_id = tenant_id

    # 调试配置
    if debug := os.environ.get("DEBUG_MODE"):
        config.debug_mode = debug.lower() in ("true", "1", "yes")

    return config


def load_config_from_file(file_path: str) -> AgentConfig:
    """
    从配置文件加载配置

    Args:
        file_path: 配置文件路径 (支持 .env, .yaml, .json)

    Returns:
        AgentConfig 实例

    注意:
        当前仅支持 .env 文件，后续可扩展 YAML/JSON
    """
    # 从 .env 文件加载
    from dotenv import load_dotenv
    load_dotenv(file_path)

    return load_config_from_env()


# ============================================================================
# 默认配置
# ============================================================================

_default_config: Optional[AgentConfig] = None


def get_config() -> AgentConfig:
    """
    获取默认配置实例

    Returns:
        AgentConfig 实例
    """
    global _default_config
    if _default_config is None:
        _default_config = load_config_from_env()
    return _default_config


def reset_config():
    """重置默认配置"""
    global _default_config
    _default_config = None


# ============================================================================
# 配置验证
# ============================================================================

def validate_config(config: AgentConfig) -> List[str]:
    """
    验证配置有效性

    Args:
        config: 要验证的配置

    Returns:
        错误消息列表 (空列表表示无错误)
    """
    errors = []

    # 验证 LLM 配置
    if not config.llm.model:
        errors.append("LLM model is not specified")

    # 验证智谱 API Key
    if not config.llm.api_key and ("glm" in config.llm.model.lower() or "zhipuai" in config.llm.model.lower()):
        errors.append("ZHIPUAI_API_KEY is required for GLM models")

    # 验证 DeepSeek API Key
    if not config.llm.api_key and "deepseek" in config.llm.model.lower():
        errors.append("DEEPSEEK_API_KEY is required for DeepSeek models")

    # 验证数据库配置
    if not config.database.url:
        errors.append("DATABASE_URL is not specified")

    # 验证温度参数
    if not 0 <= config.llm.temperature <= 2:
        errors.append("LLM temperature must be between 0 and 2")

    return errors


# ============================================================================
# 配置导出
# ============================================================================

def config_to_dict(config: AgentConfig) -> Dict[str, Any]:
    """
    将配置转换为字典

    Args:
        config: 配置实例

    Returns:
        配置字典
    """
    from dataclasses import asdict

    return asdict(config)


def config_to_env(config: AgentConfig) -> Dict[str, str]:
    """
    将配置导出为环境变量格式

    Args:
        config: 配置实例

    Returns:
        环境变量字典
    """
    env_dict = {
        "LLM_MODEL": config.llm.model,
        "LLM_TEMPERATURE": str(config.llm.temperature),
        "DATABASE_URL": config.database.url,
        "DEFAULT_TENANT_ID": config.default_tenant_id,
        "DEBUG_MODE": "true" if config.debug_mode else "false",
    }

    # 根据模型类型添加对应的 API 配置
    if "glm" in config.llm.model.lower() or "zhipuai" in config.llm.model.lower():
        env_dict.update({
            "ZHIPUAI_API_KEY": config.llm.api_key or "",
            "ZHIPUAI_BASE_URL": config.llm.base_url or "",
        })
    else:
        env_dict.update({
            "DEEPSEEK_API_KEY": config.llm.api_key or "",
            "DEEPSEEK_BASE_URL": config.llm.base_url or "",
        })

    return env_dict


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Agent Config 测试")
    print("=" * 60)

    # 获取默认配置
    config = get_config()

    print(f"\n[INFO] 默认配置:")
    print(f"  LLM Model: {config.llm.model}")
    print(f"  LLM Temperature: {config.llm.temperature}")
    print(f"  Database URL: {config.database.url[:30]}...")
    print(f"  Default Tenant: {config.default_tenant_id}")

    # 验证配置
    errors = validate_config(config)
    if errors:
        print(f"\n[WARN] 配置错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"\n[PASS] 配置验证通过")

    print("=" * 60)
