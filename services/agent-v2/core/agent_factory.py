# -*- coding: utf-8 -*-
"""
AgentFactory - DeepAgents 工厂类
================================

负责创建和管理 Data Agent V2 实例，基于 DeepAgents 框架。

核心功能:
    - create_agent(): 创建新的 DeepAgents 实例
    - get_or_create_agent(): 单例模式获取或创建 Agent
    - reset_agent(): 重置 Agent 状态

作者: BMad Master
日期: 2025-01-11
"""

import os
from typing import Optional, List, Dict, Any

# DeepAgents imports
from deepagents import create_deep_agent
from deepagents.middleware import (
    FilesystemMiddleware,
    SubAgentMiddleware
)

# LangChain imports
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

# Local imports - AgentV2 config
from ..config import agent_config as config

# ============================================================================
# AgentFactory
# ============================================================================

class AgentFactory:
    """
    DeepAgents 工厂类

    负责创建配置好的 Data Agent V2 实例，包括:
    - LLM 模型配置
    - 中间件管道
    - 工具集成
    - 租户隔离
    """

    # 类级别缓存，支持单例模式
    _cached_agents: Dict[str, Any] = {}

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        enable_filesystem: bool = True,
        enable_subagents: bool = True,
        enable_skills: bool = True
    ):
        """
        初始化 AgentFactory

        Args:
            model: LLM 模型名称 (默认从 config 读取)
            temperature: 温度参数
            max_tokens: 最大 token 数
            enable_filesystem: 是否启用文件系统中间件
            enable_subagents: 是否启用子代理中间件
            enable_skills: 是否启用技能中间件
        """
        # 从配置读取默认值
        app_config = config.get_config()
        self.model = model or app_config.llm.model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 中间件配置
        self.enable_filesystem = enable_filesystem
        self.enable_subagents = enable_subagents
        self.enable_skills = enable_skills

        # 缓存的 LLM 实例
        self._cached_llm: Optional[BaseChatModel] = None

    def create_llm(self) -> BaseChatModel:
        """
        创建 LLM 实例

        Returns:
            配置好的 LLM 实例
        """
        if self._cached_llm is None:
            # 支持多种 LLM 提供商
            if "deepseek" in self.model.lower() or "deepseek" in os.environ.get("DEEPSEEK_API_KEY", ""):
                # DeepSeek API (OpenAI 兼容)
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                )
            else:
                # 默认使用 OpenAI 或兼容接口
                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                )

        return self._cached_llm

    def _build_tools(self) -> List[BaseTool]:
        """
        构建工具列表

        Returns:
            工具列表
        """
        from ..tools.database_tools import get_database_tools

        tools = []

        # 添加数据库查询工具
        try:
            db_tools = get_database_tools()
            tools.extend(db_tools)
        except Exception as e:
            # 如果数据库工具加载失败，继续但不添加工具
            import logging
            logging.warning(f"Failed to load database tools: {e}")

        return tools

    def _build_middleware(
        self,
        tools: Optional[List[BaseTool]] = None
    ) -> List:
        """
        构建中间件管道

        Args:
            tools: 可用的工具列表

        Returns:
            中间件列表
        """
        middleware = []

        # 暂时禁用所有中间件以测试基础功能
        # # 1. 文件系统中间件 (默认启用)
        # if self.enable_filesystem:
        #     middleware.append(FilesystemMiddleware())

        # # 2. 子代理中间件 (暂时禁用，等待配置专门的子代理)
        # # if self.enable_subagents:
        # #     # TODO: 后续添加专门的子代理配置
        # #     sub_middleware = SubAgentMiddleware(
        # #         default_model=self.model,
        # #         subagents=[],  # 后续添加 SQL、图表专家子代理
        # #     )
        # #     middleware.append(sub_middleware)

        # # 3. 技能中间件 (可选)
        # if self.enable_skills and tools:
        #     # 将工具作为技能暴露
        #     pass  # TODO: 实现 SkillsMiddleware 配置

        # # 4. 自定义中间件 (后续添加)
        # # - SQLSecurityMiddleware
        # # - TenantIsolationMiddleware
        # # - XAILoggerMiddleware

        return middleware

    def create_agent(
        self,
        tenant_id: str = "default_tenant",
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None
    ):
        """
        创建 Data Agent V2 实例

        Args:
            tenant_id: 租户 ID
            tools: 可用的工具列表 (如果为 None，使用默认工具集)
            system_prompt: 自定义系统提示 (可选)

        Returns:
            DeepAgents 实例
        """
        # 创建 LLM
        llm = self.create_llm()

        # 构建工具 (如果没有提供，使用默认工具)
        if tools is None:
            tools = self._build_tools()

        # 构建中间件
        middleware = self._build_middleware(tools=tools)

        # 默认系统提示 - 告诉 Agent 关于数据库工具的信息
        if system_prompt is None:
            tool_names = [t.name for t in tools] if tools else []
            system_prompt = f"""You are a data analysis assistant with access to database query tools.

Available Tools:
{chr(10).join(f'- {name}' for name in tool_names) if tool_names else 'No tools available'}

When users ask about database information:
1. Use 'list_tables' to see all available tables
2. Use 'get_schema' to understand a table's structure
3. Use 'execute_query' to run SELECT queries and get data

IMPORTANT:
- Always explain what you're querying before using tools
- Use LIMIT in queries to avoid large result sets
- Only use SELECT queries (never INSERT, UPDATE, DELETE, etc.)
- Present results in a clear, user-friendly format
"""

        # 创建 DeepAgent
        agent = create_deep_agent(
            model=llm,
            tools=tools or [],
            middleware=middleware,
            system_prompt=system_prompt
        )

        return agent

    def get_or_create_agent(
        self,
        tenant_id: str = "default_tenant",
        tools: Optional[List[BaseTool]] = None,
        force_refresh: bool = False
    ):
        """
        获取或创建 Agent (单例模式)

        Args:
            tenant_id: 租户 ID
            tools: 可用的工具列表
            force_refresh: 是否强制刷新缓存

        Returns:
            DeepAgents 实例
        """
        cache_key = f"{tenant_id}_{id(tools) if tools else 'none'}"

        if force_refresh or cache_key not in self._cached_agents:
            self._cached_agents[cache_key] = self.create_agent(
                tenant_id=tenant_id,
                tools=tools
            )

        return self._cached_agents[cache_key]

    def reset_cache(self, tenant_id: Optional[str] = None):
        """
        重置 Agent 缓存

        Args:
            tenant_id: 指定租户 ID，None 表示清除所有
        """
        if tenant_id is None:
            self._cached_agents.clear()
        else:
            # 清除特定租户的缓存
            keys_to_remove = [
                k for k in self._cached_agents.keys()
                if k.startswith(tenant_id)
            ]
            for key in keys_to_remove:
                del self._cached_agents[key]


# ============================================================================
# 便捷函数
# ============================================================================

_default_factory: Optional[AgentFactory] = None


def get_default_factory() -> AgentFactory:
    """获取默认的 AgentFactory 实例"""
    global _default_factory
    if _default_factory is None:
        _default_factory = AgentFactory()
    return _default_factory


def create_agent(
    tenant_id: str = "default_tenant",
    tools: Optional[List[BaseTool]] = None,
    model: Optional[str] = None
):
    """
    便捷函数：快速创建 Agent

    Args:
        tenant_id: 租户 ID
        tools: 可用的工具列表
        model: LLM 模型名称 (可选)

    Returns:
        DeepAgents 实例
    """
    factory = AgentFactory(model=model) if model else get_default_factory()
    return factory.create_agent(tenant_id=tenant_id, tools=tools)
