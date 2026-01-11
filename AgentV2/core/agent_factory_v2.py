# -*- coding: utf-8 -*-
"""
AgentFactory V2 - DeepAgents 工厂类 (完整版)
=============================================

负责创建和管理 Data Agent V2 实例，基于 DeepAgents 框架。

核心功能:
    - create_agent(): 创建新的 DeepAgents 实例
    - get_or_create_agent(): 单例模式获取或创建 Agent
    - 租户隔离支持
    - SubAgent 集成

版本: 2.0.0
作者: BMad Master
"""

import os
from typing import Optional, List, Dict, Any

# DeepAgents imports
from deepagents import create_deep_agent
# 不需要导入 FilesystemMiddleware，因为 create_deep_agent 已经自动添加了
# from deepagents.middleware import FilesystemMiddleware

# LangChain imports
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

# Local imports - V2 config
from ..config import agent_config as v2_config

# Local imports - V2 modules
from ..middleware import (
    TenantIsolationMiddleware,
    SQLSecurityMiddleware
)
from ..subagents import SubAgentManager, create_subagent_manager

# ============================================================================
# AgentFactory
# ============================================================================

class AgentFactory:
    """
    DeepAgents 工厂类 V2

    新增功能:
        - 租户隔离中间件集成
        - SubAgent 支持
        - 自定义中间件管道
    """

    # 类级别缓存
    _cached_agents: Dict[str, Any] = {}
    _cached_llm: Optional[BaseChatModel] = None

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        enable_tenant_isolation: bool = True,
        enable_sql_security: bool = True,
        enable_subagents: bool = True
    ):
        """
        初始化 AgentFactory

        Args:
            model: LLM 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            enable_tenant_isolation: 是否启用租户隔离
            enable_sql_security: 是否启用 SQL 安全
            enable_subagents: 是否启用子代理 (已由 create_deep_agent 自动管理)
        """
        # 从 V2 配置读取默认值
        app_config = v2_config.get_config()
        self.model = model or app_config.llm.model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 功能开关
        self.enable_tenant_isolation = enable_tenant_isolation
        self.enable_sql_security = enable_sql_security
        self.enable_subagents = enable_subagents

        # SubAgent 管理器
        self._subagent_manager: Optional[SubAgentManager] = None

    @property
    def subagent_manager(self) -> SubAgentManager:
        """获取或创建 SubAgent 管理器"""
        if self._subagent_manager is None:
            self._subagent_manager = create_subagent_manager(default_model=self.model)
        return self._subagent_manager

    def create_llm(self) -> BaseChatModel:
        """创建 LLM 实例"""
        if self._cached_llm is None:
            if "deepseek" in self.model.lower():
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                )
            else:
                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                )

        return self._cached_llm

    def _build_middleware(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None
    ) -> List[Any]:
        """
        构建中间件管道

        注意: create_deep_agent 已经自动添加了以下中间件:
            - TodoListMiddleware
            - FilesystemMiddleware
            - SubAgentMiddleware
            - SummarizationMiddleware
            - AnthropicPromptCachingMiddleware
            - PatchToolCallsMiddleware

        因此这里只需要添加我们的自定义中间件。

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用工具列表

        Returns:
            中间件列表
        """
        middleware = []

        # 1. 租户隔离中间件 (第一优先级)
        if self.enable_tenant_isolation and tenant_id:
            tenant_middleware = TenantIsolationMiddleware(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id
            )
            middleware.append(tenant_middleware)

        # 2. SQL 安全中间件
        if self.enable_sql_security:
            sql_middleware = SQLSecurityMiddleware()
            middleware.append(sql_middleware)

        # 注意: 不需要添加 FilesystemMiddleware，因为 create_deep_agent 已经自动添加了
        # 注意: 不需要添加 SubAgentMiddleware，因为 create_deep_agent 已经自动添加了

        return middleware

    def create_agent(
        self,
        tenant_id: str = "default_tenant",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None
    ):
        """
        创建 Data Agent V2 实例

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表
            system_prompt: 自定义系统提示

        Returns:
            DeepAgents 实例
        """
        # 创建 LLM
        llm = self.create_llm()

        # 构建中间件
        middleware = self._build_middleware(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            tools=tools
        )

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
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        force_refresh: bool = False
    ):
        """
        获取或创建 Agent (单例模式)

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表
            force_refresh: 是否强制刷新

        Returns:
            DeepAgents 实例
        """
        cache_key = f"{tenant_id}_{user_id or 'none'}_{session_id or 'none'}"

        if force_refresh or cache_key not in self._cached_agents:
            self._cached_agents[cache_key] = self.create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                tools=tools
            )

        return self._cached_agents[cache_key]

    def reset_cache(self, tenant_id: Optional[str] = None):
        """重置 Agent 缓存"""
        if tenant_id is None:
            self._cached_agents.clear()
        else:
            keys_to_remove = [
                k for k in self._cached_agents.keys()
                if k.startswith(tenant_id)
            ]
            for key in keys_to_remove:
                del self._cached_agents[key]

    def setup_default_subagents(
        self,
        postgres_tools: Optional[List[BaseTool]] = None,
        echarts_tools: Optional[List[BaseTool]] = None,
        file_tools: Optional[List[BaseTool]] = None
    ):
        """
        设置默认的 SubAgent

        Args:
            postgres_tools: PostgreSQL 工具
            echarts_tools: ECharts 工具
            file_tools: 文件处理工具
        """
        self.subagent_manager.create_default_subagents(
            postgres_tools=postgres_tools or [],
            echarts_tools=echarts_tools or [],
            file_tools=file_tools or []
        )


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
    user_id: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    model: Optional[str] = None
):
    """
    便捷函数：快速创建 Agent

    Args:
        tenant_id: 租户 ID
        user_id: 用户 ID
        tools: 可用的工具列表
        model: LLM 模型名称

    Returns:
        DeepAgents 实例
    """
    factory = AgentFactory(model=model) if model else get_default_factory()
    return factory.create_agent(tenant_id=tenant_id, user_id=user_id, tools=tools)
