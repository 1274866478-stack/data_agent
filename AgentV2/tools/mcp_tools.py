# -*- coding: utf-8 -*-
"""
MCP Tools Wrapper - MCP 工具包装器
==================================

将 Model Context Protocol (MCP) 工具包装为 LangChain Tools。

核心功能:
    - get_mcp_tools(): 获取 MCP 服务器提供的工具
    - wrap_mcp_tools(): 将 MCP 工具包装为 LangChain 格式

作者: BMad Master
版本: 2.0.0
"""

import os
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool

# ============================================================================
# MCP 工具配置
# ============================================================================

def get_default_mcp_config() -> Dict[str, Dict[str, Any]]:
    """
    获取默认的 MCP 服务器配置

    Returns:
        MCP 服务器配置字典
    """
    return {
        "postgres": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-postgres", get_database_url()],
        },
        "echarts": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-echarts"]
        }
    }


def get_database_url() -> str:
    """
    获取数据库连接 URL

    优先级: 环境变量 > 默认值
    """
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/data_agent"
    )


# ============================================================================
# MCP 工具获取
# ============================================================================

async def get_mcp_tools(
    database_url: Optional[str] = None,
    enable_postgres: bool = True,
    enable_echarts: bool = True
) -> List[BaseTool]:
    """
    获取 MCP 工具列表

    Args:
        database_url: 数据库连接 URL
        enable_postgres: 是否启用 PostgreSQL 工具
        enable_echarts: 是否启用 ECharts 工具

    Returns:
        LangChain Tool 列表

    注意:
        实际实现需要连接到 MCP 服务器。
        这里提供框架代码，具体集成需要根据 MCP 协议实现。
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient

    # 构建配置
    config = {}
    if enable_postgres:
        config["postgres"] = {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-postgres", database_url or get_database_url()],
        }
    if enable_echarts:
        config["echarts"] = {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-echarts"]
        }

    # 创建 MCP 客户端
    client = MultiServerMCPClient(config)

    # 获取工具
    tools = await client.get_tools()

    return tools


def wrap_mcp_tools(mcp_tools: List[Any]) -> List[BaseTool]:
    """
    将 MCP 工具包装为 LangChain Tools

    Args:
        mcp_tools: MCP 原始工具列表

    Returns:
        LangChain Tool 列表
    """
    wrapped_tools = []

    for tool in mcp_tools:
        # 如果已经是 LangChain Tool，直接添加
        if isinstance(tool, BaseTool):
            wrapped_tools.append(tool)
        else:
            # 否则进行包装
            # 这里需要根据实际 MCP 工具格式进行适配
            pass

    return wrapped_tools


# ============================================================================
# 便捷函数
# ============================================================================

async def get_tools_for_agent(
    database_url: Optional[str] = None
) -> List[BaseTool]:
    """
    获取 Agent 所需的完整工具集

    Args:
        database_url: 数据库连接 URL

    Returns:
        LangChain Tool 列表
    """
    tools = await get_mcp_tools(database_url=database_url)
    return wrap_mcp_tools(tools)


# ============================================================================
# 同步版本 (用于不支持 async 的场景)
# ============================================================================

def get_mcp_tools_sync(
    database_url: Optional[str] = None
) -> List[BaseTool]:
    """
    同步版本的 MCP 工具获取

    Args:
        database_url: 数据库连接 URL

    Returns:
        LangChain Tool 列表 (空列表，需要实际实现)
    """
    # TODO: 实现同步版本
    # 目前返回空列表，实际使用时需要实现
    return []


if __name__ == "__main__":
    import asyncio

    async def test():
        print("=" * 60)
        print("MCP Tools 测试")
        print("=" * 60)

        # 测试配置
        config = get_default_mcp_config()
        print(f"\n[INFO] MCP 配置:")
        for name, cfg in config.items():
            print(f"  - {name}: {cfg['command']} {' '.join(cfg['args'][:2])}...")

        # 注意：实际获取工具需要有效的数据库连接
        print("\n[INFO] 实际工具获取需要:")
        print("  1. 有效的数据库连接")
        print("  2. MCP 服务器运行中")
        print("  3. Node.js 和 npx 可用")

    asyncio.run(test())
