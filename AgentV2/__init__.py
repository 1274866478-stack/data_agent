# -*- coding: utf-8 -*-
"""
AgentV2 - Data Agent V2 based on DeepAgents
============================================

多租户 SaaS 数据智能分析平台的第二代 AI Agent。

基于 LangChain DeepAgents 框架重构，提供：
    - 智能子代理委派
    - 内置中间件管道
    - MCP 工具集成
    - 多租户隔离

快速开始:
    ```python
    from AgentV2 import create_agent
    from AgentV2.tools import get_mcp_tools

    # 创建 Agent
    agent = create_agent(tenant_id="my_tenant")

    # 执行查询
    result = agent.invoke({"messages": [("user", "查询用户数据")]})
    ```

作者: BMad Master
版本: 2.0.0
"""

__version__ = "2.0.0"

# 核心导出
from .core import AgentFactory, create_agent, get_default_factory
from .config import AgentConfig, get_config
from .middleware import SQLSecurityMiddleware, TenantIsolationMiddleware
from .subagents import SubAgentManager, create_subagent_manager

__all__ = [
    # 核心类
    "AgentFactory",
    "create_agent",
    "get_default_factory",

    # 配置
    "AgentConfig",
    "get_config",

    # 中间件
    "SQLSecurityMiddleware",
    "TenantIsolationMiddleware",

    # SubAgent
    "SubAgentManager",
    "create_subagent_manager",
]
