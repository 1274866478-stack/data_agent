"""
Agent Service V5 - Secure SQL Agent with LangGraph
Integrates security firewall, business logic prompts, and golden examples.

Key Security Features:
- SQL sanitization before execution (removes HTML, markdown, CSS pollution)
- Validation layer (SELECT only, blacklist dangerous keywords)
- Recursion limit to prevent infinite loops
- Business logic enforcement via prompts and examples

V5.1 Updates:
- Integrated VisualizationResponse for structured output
- Added data transformer for MCP ECharts integration
- Unified response format with chart configuration
"""
import asyncio
import json
import logging
import os
import re
import sys
import traceback
from typing import Literal, Optional, Dict, Any, List

import anyio

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from src.app.core.config import settings
from openai import AuthenticationError as OpenAIAuthenticationError

# Import V5 security modules
from .prompts import get_system_prompt
from .tools import (
    sanitize_sql,
    validate_sql_safety,
    execute_sql_safe,
    get_table_schema,
    list_available_tables,
    set_mcp_client,
    analyze_dataframe,
)
from .examples import load_golden_examples

# Import V5.1 visualization modules
from .models import (
    VisualizationResponse,
    QueryResult,
    ChartConfig,
    ChartType,
    AgentRequest,
    EChartsOption,
)
from .data_transformer import (
    prepare_mcp_chart_request,
    infer_chart_type,
    sql_result_to_mcp_echarts_data,
    sql_result_to_echarts_data,
)
from .response_formatter import format_api_response, format_error_response

logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================

# Maximum iterations to prevent infinite loops
MAX_RECURSION_LIMIT = 15

# LLM Configuration
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0


# ============================================================
# Agent State & Cache (Singleton Pattern)
# ============================================================

_cached_agent = None
_cached_mcp_client = None
_cached_tools: List[BaseTool] = []
_cached_checkpointer = None


class MCPClientWrapper:
    """
    Wrapper for MCP client that provides a consistent interface.
    This allows tools.py to call MCP without direct dependency.
    """

    def __init__(self, mcp_client):
        self._client = mcp_client
        self._tools_map: Dict[str, Any] = {}

    async def initialize(self, tools: Optional[List[BaseTool]] = None):
        """Initialize and cache tool references.

        Args:
            tools: Pre-fetched tools (e.g., with injected fallbacks). If None,
                tools will be pulled from MCP client directly.
        """
        if tools is None:
            tools = await self._client.get_tools()
        for tool in tools:
            self._tools_map[tool.name] = self._ensure_sync_tool(tool)
            print(
                f"[MCP init] tool={getattr(tool, 'name', tool)} "
                f"type={type(tool)} has_invoke={hasattr(tool, 'invoke')} has_ainvoke={hasattr(tool, 'ainvoke')}"
            )
            try:
                print(f"[MCP args_schema] tool={getattr(tool, 'name', tool)} schema={getattr(tool, 'args_schema', None)}")
            except Exception as e:
                print(f"[MCP args_schema] tool={getattr(tool, 'name', tool)} read_error={e}")
        return tools

    def _ensure_sync_tool(self, tool: BaseTool) -> BaseTool:
        """Wrap MCP tool to expose both sync/async invocation."""
        class SyncAdapter(BaseTool):
            name: str = tool.name
            description: str = getattr(tool, "description", "")
            args_schema: Optional[type] = getattr(tool, "args_schema", None)

            def _run(self, tool_input=None, *args, **kwargs):
                # LangChain may pass structured args via kwargs when args_schema exists.
                if kwargs:
                    if tool_input is None:
                        tool_input = kwargs
                    elif isinstance(tool_input, dict):
                        tool_input = {**tool_input, **kwargs}
                    kwargs = {}
                if hasattr(tool, "ainvoke"):
                    try:
                        return asyncio.run(tool.ainvoke(tool_input, **kwargs))
                    except RuntimeError:
                        try:
                            return anyio.from_thread.run(tool.ainvoke, tool_input, **kwargs)
                        except BaseException as e:
                            # Catch all exceptions including ExceptionGroup from anyio
                            error_msg = str(e)
                            # Extract underlying exception if it's an ExceptionGroup
                            if hasattr(e, "exceptions") and e.exceptions:
                                # This is an ExceptionGroup (Python 3.11+)
                                underlying_errors = [str(exc) for exc in e.exceptions]
                                error_msg = f"Tool execution failed: {', '.join(underlying_errors)}"
                            elif "TaskGroup" in error_msg or "sub-exception" in error_msg:
                                # Try to get more details from the exception
                                if hasattr(e, "__cause__") and e.__cause__:
                                    error_msg = f"Tool execution failed: {str(e.__cause__)}"
                                else:
                                    error_msg = "Tool execution failed: 工具执行过程中发生错误"
                            logger.error(f"Tool execution failed in anyio.from_thread: {error_msg}", exc_info=True)
                            # Return error message instead of raising
                            return f"Error executing tool: {error_msg}"
                if hasattr(tool, "invoke"):
                    try:
                        return tool.invoke(tool_input, **kwargs)
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}", exc_info=True)
                        return f"Error executing tool: {str(e)}"
                raise RuntimeError("Tool has neither invoke nor ainvoke")

            async def _arun(self, tool_input=None, *args, **kwargs):
                if kwargs:
                    if tool_input is None:
                        tool_input = kwargs
                    elif isinstance(tool_input, dict):
                        tool_input = {**tool_input, **kwargs}
                    kwargs = {}
                if hasattr(tool, "ainvoke"):
                    try:
                        result = await tool.ainvoke(tool_input, **kwargs)
                        # 🔴 第一道防线：检查空数据
                        if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                            logger.warning(f"⚠️ [第一道防线] 工具 {getattr(tool, 'name', 'unknown')} 返回空数据")
                            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                        return result
                    except BaseException as e:
                        # 🔴 第一道防线：异常处理 - 返回特定错误字符串
                        error_msg = str(e)
                        # Extract underlying exception if it's an ExceptionGroup
                        if hasattr(e, "exceptions") and e.exceptions:
                            # This is an ExceptionGroup (Python 3.11+)
                            underlying_errors = [str(exc) for exc in e.exceptions]
                            error_msg = f"Tool execution failed: {', '.join(underlying_errors)}"
                        elif "TaskGroup" in error_msg or "sub-exception" in error_msg:
                            # Try to get more details from the exception
                            if hasattr(e, "__cause__") and e.__cause__:
                                error_msg = f"Tool execution failed: {str(e.__cause__)}"
                            else:
                                error_msg = "Tool execution failed: 工具执行过程中发生错误"
                        logger.error(f"⚠️ [第一道防线] 工具执行异常: {error_msg}", exc_info=True)
                        # 返回特定错误字符串，强制LLM停止生成答案
                        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                if hasattr(tool, "invoke"):
                    try:
                        result = await asyncio.to_thread(tool.invoke, tool_input, **kwargs)
                        # 🔴 第一道防线：检查空数据
                        if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                            logger.warning(f"⚠️ [第一道防线] 工具 {getattr(tool, 'name', 'unknown')} 返回空数据")
                            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                        return result
                    except Exception as e:
                        logger.error(f"⚠️ [第一道防线] 工具线程执行异常: {e}", exc_info=True)
                        # 返回特定错误字符串，强制LLM停止生成答案
                        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                raise RuntimeError("Tool has neither invoke nor ainvoke")

        wrapped = SyncAdapter()
        print(
            f"[MCP wrap] tool={getattr(tool, 'name', tool)} -> wrapped "
            f"has_invoke={hasattr(wrapped, 'invoke')} has_ainvoke={hasattr(wrapped, 'ainvoke')}"
        )
        return wrapped

    def execute_query(self, sql: str) -> str:
        """Execute SQL query via MCP postgres server."""
        if "query" not in self._tools_map:
            raise RuntimeError("MCP query tool not available")
        # The actual execution happens through LangGraph's ToolNode
        # This is called by our safe wrapper
        # MCP postgres expects structured input (JSON object with "sql")
        return self._tools_map["query"].invoke({"sql": sql})

    def get_schema(self, table_name: str) -> str:
        """Get table schema via MCP."""
        if "get_schema" in self._tools_map:
            return self._tools_map["get_schema"].invoke({"table_name": table_name})
        # Fallback: use query tool to fetch schema
        if "query" not in self._tools_map:
            raise RuntimeError("MCP query tool not available for fallback get_schema")
        # basic sanitization to avoid injection in fallback
        if not re.match(r"^[A-Za-z0-9_]+$", table_name):
            return "Invalid table name"
        sql = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        return self._tools_map["query"].invoke({"sql": sql})

    def list_tables(self) -> str:
        """List all tables via MCP."""
        if "list_tables" in self._tools_map:
            return self._tools_map["list_tables"].invoke({})
        # Fallback: use query tool to fetch tables
        if "query" not in self._tools_map:
            raise RuntimeError("MCP query tool not available for fallback list_tables")
        sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema','pg_catalog')
          AND table_type='BASE TABLE'
        ORDER BY table_name
        """
        return self._tools_map["query"].invoke({"sql": sql})


# ============================================================
# LLM Factory
# ============================================================

def create_llm(
    model: str = None,
    temperature: float = None,
    api_key: str = None,
    base_url: str = None,
    provider: str = None,
) -> ChatOpenAI:
    """
    Create LLM instance with secure defaults.

    Args:
        model: Model name (default: deepseek-chat)
        temperature: Temperature setting (default: 0 for deterministic output)
        api_key: API key (default: from settings)
        base_url: API base URL (default: from settings)

    Returns:
        Configured ChatOpenAI instance
    """
    provider = provider or getattr(settings, "llm_provider", "deepseek")
    provider = provider.lower() if provider else "deepseek"
    # 如果 deepseek 不可用但有智谱密钥，自动切到 zhipu 以提升可用性
    if provider == "deepseek" and getattr(settings, "zhipuai_api_key", None):
        provider = "zhipu"

    if provider == "zhipu":
        return ChatOpenAI(
            model=model or getattr(settings, "zhipuai_default_model", "glm-4.6"),
            api_key=api_key or getattr(settings, "zhipuai_api_key", ""),
            base_url=base_url or getattr(settings, "zhipuai_base_url", "https://open.bigmodel.cn/api/paas/v4"),
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
            timeout=getattr(settings, "zhipuai_timeout", 300),  # 🔥 Token Expansion: 增加超时时间到 300 秒（5分钟）以支持长文本生成
            max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 🔥 Token Expansion: 提升最大输出 Token 限制到 8192，确保完整的 ECharts JSON 配置输出
        )

    if provider == "openrouter":
        return ChatOpenAI(
            model=model or getattr(settings, "openrouter_default_model", "google/gemini-2.0-flash-exp"),
            api_key=api_key or getattr(settings, "openrouter_api_key", ""),
            base_url=base_url or getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1"),
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
            timeout=getattr(settings, "openrouter_timeout", 300),  # 🔥 Token Expansion: 增加超时时间到 300 秒（5分钟）以支持长文本生成
            max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 🔥 Token Expansion: 提升最大输出 Token 限制到 8192，确保完整的 ECharts JSON 配置输出
        )

    # default: deepseek
    return ChatOpenAI(
        model=model or getattr(settings, 'DEEPSEEK_MODEL', DEFAULT_MODEL),
        api_key=api_key or getattr(settings, 'DEEPSEEK_API_KEY', ''),
        base_url=base_url or getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        timeout=getattr(settings, "deepseek_timeout", 300),  # 🔥 Token Expansion: 增加超时时间到 300 秒（5分钟）以支持长文本生成
        max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 🔥 Token Expansion: 提升最大输出 Token 限制到 8192，确保完整的 ECharts JSON 配置输出
    )


# ============================================================
# MCP Configuration
# ============================================================

def get_mcp_config(database_url: str, enable_echarts: bool = False) -> Dict[str, Any]:
    """
    Build MCP server configuration.

    Args:
        database_url: PostgreSQL connection string
        enable_echarts: Whether to enable ECharts MCP server

    Returns:
        MCP configuration dictionary
    """
    # Fix Windows npx command issue: use npx.cmd on Windows
    npx_command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    config = {
        "postgres": {
            "transport": "stdio",
            "command": npx_command,
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                database_url
            ],
        }
    }

    if enable_echarts:
        # 检查 MCP ECharts URL 环境变量
        mcp_echarts_url_env = os.getenv("MCP_ECHARTS_URL")
        logger.info(f"🔍 Checking MCP Config: MCP_ECHARTS_URL={mcp_echarts_url_env}")
        
        # 支持环境变量配置，Docker 环境中使用服务名称
        echarts_url = mcp_echarts_url_env or "http://mcp_echarts:3033/sse"  # Docker 环境默认使用服务名称
        # 如果 URL 包含 localhost，可能是本地开发环境，保持原样
        if "localhost" in echarts_url or "127.0.0.1" in echarts_url:
            echarts_url = "http://localhost:3033/sse"
        
        logger.info(f"🔍 MCP ECharts configuration: enable_echarts={enable_echarts}, url={echarts_url}")
        
        config["echarts"] = {
            "transport": "sse",
            "url": echarts_url,
            "timeout": 60.0,  # 🔥 第二步修复：增加 MCP ECharts 连接超时到 60 秒
            "sse_read_timeout": 180.0,  # 🔥 第二步修复：增加 SSE 读取超时到 180 秒
        }
    else:
        logger.info(f"🔍 MCP ECharts disabled: enable_echarts={enable_echarts}")

    return config


# ============================================================
# Secure Tool Wrapper
# ============================================================

def _wrap_tool_for_langgraph(t: BaseTool) -> BaseTool:
    """
    Ensure tool exposes both sync invoke/run and async ainvoke/arun so ToolNode
    won't complain about StructuredTool lacking sync invocation.
    """
    class WrappedTool(BaseTool):
        name: str = t.name
        description: str = getattr(t, "description", "")
        args_schema: Optional[type] = getattr(t, "args_schema", None)

        def _run(self, tool_input=None, *args, **kwargs):
            if kwargs:
                if tool_input is None:
                    tool_input = kwargs
                elif isinstance(tool_input, dict):
                    tool_input = {**tool_input, **kwargs}
                kwargs = {}
            if tool_input is None:
                tool_input = {}
            if hasattr(t, "ainvoke"):
                try:
                    return asyncio.run(t.ainvoke(tool_input, **kwargs))
                except RuntimeError:
                    # already in loop -> run in thread
                    return anyio.from_thread.run(t.ainvoke, tool_input, **kwargs)
            if hasattr(t, "invoke"):
                return t.invoke(tool_input, **kwargs)
            raise RuntimeError("Tool has neither invoke nor ainvoke")

        async def _arun(self, tool_input=None, *args, **kwargs):
            if kwargs:
                if tool_input is None:
                    tool_input = kwargs
                elif isinstance(tool_input, dict):
                    tool_input = {**tool_input, **kwargs}
                kwargs = {}
            if tool_input is None:
                tool_input = {}
            if hasattr(t, "ainvoke"):
                try:
                    result = await t.ainvoke(tool_input, **kwargs)
                    # 🔴 第一道防线：检查空数据
                    if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                        logger.warning(f"⚠️ [第一道防线] 工具 {getattr(t, 'name', 'unknown')} 返回空数据")
                        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                    return result
                except Exception as e:
                    logger.error(f"⚠️ [第一道防线] 工具执行异常: {e}", exc_info=True)
                    return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
            if hasattr(t, "invoke"):
                try:
                    result = await asyncio.to_thread(t.invoke, tool_input, **kwargs)
                    # 🔴 第一道防线：检查空数据
                    if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                        logger.warning(f"⚠️ [第一道防线] 工具 {getattr(t, 'name', 'unknown')} 返回空数据")
                        return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                    return result
                except Exception as e:
                    logger.error(f"⚠️ [第一道防线] 工具线程执行异常: {e}", exc_info=True)
                    return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
            raise RuntimeError("Tool has neither invoke nor ainvoke")

    return WrappedTool()


def _wrap_inspect_file_tool(t: BaseTool) -> BaseTool:
    """
    Special wrapper for inspect_file tool that returns specific error message
    when file cannot be read or result is empty.
    """
    class WrappedInspectFileTool(BaseTool):
        name: str = t.name
        description: str = getattr(t, "description", "")
        args_schema: Optional[type] = getattr(t, "args_schema", None)

        def _run(self, tool_input=None, *args, **kwargs):
            if kwargs:
                if tool_input is None:
                    tool_input = kwargs
                elif isinstance(tool_input, dict):
                    tool_input = {**tool_input, **kwargs}
                kwargs = {}
            if tool_input is None:
                tool_input = {}
            try:
                if hasattr(t, "ainvoke"):
                    try:
                        result = asyncio.run(t.ainvoke(tool_input, **kwargs))
                    except RuntimeError:
                        result = anyio.from_thread.run(t.ainvoke, tool_input, **kwargs)
                elif hasattr(t, "invoke"):
                    result = t.invoke(tool_input, **kwargs)
                else:
                    raise RuntimeError("Tool has neither invoke nor ainvoke")
                
                # 🔴 第一道防线：检查空数据或错误
                if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                    logger.warning(f"⚠️ [第一道防线] inspect_file 返回空数据")
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
                # 检查是否是错误信息
                if isinstance(result, str) and (result.startswith("错误") or result.startswith("Error") or "失败" in result or "not found" in result.lower() or "不存在" in result):
                    logger.warning(f"⚠️ [第一道防线] inspect_file 返回错误: {result}")
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
                return result
            except Exception as e:
                logger.error(f"⚠️ [第一道防线] inspect_file 执行异常: {e}", exc_info=True)
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'

        async def _arun(self, tool_input=None, *args, **kwargs):
            if kwargs:
                if tool_input is None:
                    tool_input = kwargs
                elif isinstance(tool_input, dict):
                    tool_input = {**tool_input, **kwargs}
                kwargs = {}
            if tool_input is None:
                tool_input = {}
            try:
                if hasattr(t, "ainvoke"):
                    result = await t.ainvoke(tool_input, **kwargs)
                elif hasattr(t, "invoke"):
                    result = await asyncio.to_thread(t.invoke, tool_input, **kwargs)
                else:
                    raise RuntimeError("Tool has neither invoke nor ainvoke")
                
                # 🔴 第一道防线：检查空数据或错误
                if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                    logger.warning(f"⚠️ [第一道防线] inspect_file 返回空数据")
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
                # 检查是否是错误信息
                if isinstance(result, str) and (result.startswith("错误") or result.startswith("Error") or "失败" in result or "not found" in result.lower() or "不存在" in result):
                    logger.warning(f"⚠️ [第一道防线] inspect_file 返回错误: {result}")
                    return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
                return result
            except Exception as e:
                logger.error(f"⚠️ [第一道防线] inspect_file 执行异常: {e}", exc_info=True)
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'

    return WrappedInspectFileTool()


def create_secure_tools(mcp_tools: List[BaseTool]) -> List[BaseTool]:
    """
    Wrap MCP tools with security layer.

    The 'query' tool is replaced with our sanitized version.
    File data source tools (analyze_dataframe, inspect_file) are replaced with custom versions
    that handle MinIO file paths correctly.

    Args:
        mcp_tools: Raw tools from MCP client

    Returns:
        List of secured tools
    """

    secure_tools = []

    for tool in mcp_tools:
        if tool.name == "query":
            # Replace with our secure wrapper
            logger.info("Replacing 'query' tool with secure execute_sql_safe")
            secure_tools.append(_wrap_tool_for_langgraph(execute_sql_safe))
        elif tool.name == "get_schema":
            secure_tools.append(_wrap_tool_for_langgraph(get_table_schema))
        elif tool.name == "list_tables":
            secure_tools.append(_wrap_tool_for_langgraph(list_available_tables))
        elif tool.name == "analyze_dataframe":
            # Replace with our custom version that handles MinIO file paths
            logger.info("Replacing 'analyze_dataframe' tool with custom MinIO-aware version")
            secure_tools.append(_wrap_tool_for_langgraph(analyze_dataframe))
        elif tool.name == "inspect_file":
            # Replace with special wrapper that returns specific error message
            logger.info("Replacing 'inspect_file' tool with anti-hallucination wrapper")
            secure_tools.append(_wrap_inspect_file_tool(tool))
        else:
            # Pass through other tools (e.g., echarts, etc.)
            logger.info(f"Passing through tool: {tool.name}")
            secure_tools.append(_wrap_tool_for_langgraph(tool))

    return secure_tools


# ============================================================
# Agent Builder
# ============================================================

async def build_agent(
    database_url: str,
    enable_echarts: bool = False,
    model: str = None,
) -> tuple:
    """
    Build and compile the LangGraph agent.

    Args:
        database_url: PostgreSQL connection string
        enable_echarts: Enable chart generation
        model: LLM model to use

    Returns:
        Tuple of (compiled_agent, mcp_client)
    """
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer

    # Return cached if available
    if _cached_agent is not None and _cached_mcp_client is not None:
        logger.info("Using cached agent instance")
        return _cached_agent, _cached_mcp_client

    logger.info("Building new agent instance...")

    # Import MCP client (lazy import to avoid startup issues)
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        raise RuntimeError("langchain-mcp-adapters not installed")

    # Create MCP client
    mcp_config = get_mcp_config(database_url, enable_echarts)
    _cached_mcp_client = MultiServerMCPClient(mcp_config)

    disable_tools = os.getenv("DISABLE_MCP_TOOLS", "false").lower() == "true"

    if not disable_tools:
        # Initialize MCP and get tools
        try:
            raw_tools = await _cached_mcp_client.get_tools()
        except Exception as e:
            # 检查是否是连接错误（如 ClientConnectorError）
            error_type = type(e).__name__
            error_message = str(e)
            
            # 检查是否是连接相关的错误
            is_connection_error = (
                "ClientConnectorError" in error_type or
                "ConnectionError" in error_type or
                "ConnectionRefusedError" in error_type or
                "无法连接" in error_message or
                "connection" in error_message.lower() or
                "refused" in error_message.lower()
            )
            
            if is_connection_error and enable_echarts and "echarts" in mcp_config:
                logger.error(
                    "❌ 无法连接到 MCP ECharts 服务，请检查 Docker 容器是否启动。"
                    f"错误类型: {error_type}, 错误信息: {error_message}",
                    exc_info=True,
                )
            else:
                logger.warning(
                    f"Failed to load MCP tools; will retry without echarts if enabled. "
                    f"错误类型: {error_type}, 错误信息: {error_message}",
                    exc_info=True,
                )
            
            # If echarts was enabled, retry without it to keep SQL path working
            if enable_echarts and "echarts" in mcp_config:
                logger.info("⚠️ 尝试回退：禁用 ECharts 服务，仅使用 PostgreSQL MCP 工具")
                fallback_config = {k: v for k, v in mcp_config.items() if k != "echarts"}
                _cached_mcp_client = MultiServerMCPClient(fallback_config)
                try:
                    raw_tools = await _cached_mcp_client.get_tools()
                    logger.info("✅ 回退成功：已加载 PostgreSQL MCP 工具（不含 ECharts）")
                except Exception as fallback_error:
                    logger.error(
                        f"❌ 回退失败：即使禁用 ECharts 后仍无法加载 MCP 工具。错误: {fallback_error}",
                        exc_info=True,
                    )
                    raise
            else:
                raise
        logger.info(f"Loaded {len(raw_tools)} tools from MCP")
        for t in raw_tools:
            logger.info(
                "MCP tool loaded",
                extra={
                    "tool_name": getattr(t, "name", str(t)),
                    "tool_type": str(type(t)),
                    "has_invoke": hasattr(t, "invoke"),
                    "has_ainvoke": hasattr(t, "ainvoke"),
                },
            )

        # Inject fallbacks if MCP server did not expose schema/table tools
        has_list_tables = any(getattr(t, "name", "") in ("list_tables", "list_available_tables") for t in raw_tools)
        if not has_list_tables:
            logger.warning("MCP server missing list_tables; injecting fallback tool")
            raw_tools.append(list_available_tables)

        has_get_schema = any(getattr(t, "name", "") in ("get_schema", "get_table_schema") for t in raw_tools)
        if not has_get_schema:
            logger.warning("MCP server missing get_schema; injecting fallback tool")
            raw_tools.append(get_table_schema)

        # Wrap with security layer
        mcp_wrapper = MCPClientWrapper(_cached_mcp_client)
        # initialize with injected fallback tools
        await mcp_wrapper.initialize(raw_tools)
        set_mcp_client(mcp_wrapper)

        # Create secure tools
        _cached_tools = create_secure_tools(raw_tools)
    else:
        logger.warning("DISABLE_MCP_TOOLS=true, building agent without tools")
        _cached_tools = []

    # Create LLM with tools
    preferred_provider = getattr(settings, "llm_provider", "deepseek")
    llm = create_llm(model=model, provider=preferred_provider)
    llm_with_tools = llm.bind_tools(_cached_tools) if _cached_tools else llm

    # Get system prompt with golden examples
    system_prompt = get_system_prompt()

    # Define agent node
    async def call_model(state: MessagesState) -> Dict[str, List]:
        messages = state["messages"]

        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages

        try:
            response = await llm_with_tools.ainvoke(messages)
        except OpenAIAuthenticationError as e:
            logger.warning(
                "LLM authentication failed for provider %s, falling back to zhipu",
                preferred_provider,
                exc_info=True,
            )
            fallback_llm = create_llm(model=model, provider="zhipu")
            fallback_llm_with_tools = (
                fallback_llm.bind_tools(_cached_tools) if _cached_tools else fallback_llm
            )
            response = await fallback_llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # Define routing logic
    def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build graph
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_edge(START, "agent")

    if _cached_tools:
        tool_node = ToolNode(_cached_tools)
        builder.add_node("tools", tool_node)
        builder.add_conditional_edges("agent", should_continue)
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)

    # Compile with checkpointer and recursion limit
    _cached_checkpointer = MemorySaver()
    _cached_agent = builder.compile(checkpointer=_cached_checkpointer)

    logger.info("Agent built successfully")
    return _cached_agent, _cached_mcp_client



async def reset_agent():
    """
    Reset agent cache. Call this when:
    - Database connection changes
    - Configuration updates
    - Error recovery needed
    """
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer

    _cached_agent = None
    _cached_mcp_client = None
    _cached_tools = []
    _cached_checkpointer = None

    logger.info("Agent cache reset")


# ============================================================
# Agent Execution
# ============================================================

async def run_agent(
    question: str,
    database_url: str,
    thread_id: str = "default",
    enable_echarts: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run the SQL agent with a user question.

    Args:
        question: User's natural language question
        database_url: PostgreSQL connection string
        thread_id: Session/conversation ID for memory
        enable_echarts: Enable chart generation
        verbose: Enable detailed logging

    Returns:
        Response dictionary with:
        - answer: AI's text response
        - sql: Executed SQL query (if any)
        - data: Query results (if any)
        - success: Whether execution succeeded
        - error: Error message (if failed)
    """
    try:
        # Build or get cached agent
        agent, _ = await build_agent(
            database_url=database_url,
            enable_echarts=enable_echarts,
        )

        # Configure session
        config = {"configurable": {"thread_id": thread_id}}

        if verbose:
            logger.info(f"Running agent with question: {question[:100]}...")

        # Collect all messages during execution
        all_messages = []
        final_content = ""
        executed_sql = None
        query_results = None
        chart_image = None  # Store chart image from MCP ECharts tool call

        # Stream execution
        try:
            async for step in agent.astream(
                {"messages": [HumanMessage(content=question)]},
                config,
                stream_mode="updates",
            ):
                for node_name, node_output in step.items():
                    if verbose:
                        logger.debug(f"Step from node: {node_name}")

                    if "messages" in node_output:
                        messages = node_output["messages"]
                        all_messages.extend(messages)

                        for msg in messages:
                            # 🔥🔥 DEBUG: 打印所有消息类型
                            import sys
                            print(f"🔥🔥 MESSAGE TYPE: {type(msg).__name__}", flush=True)
                            if isinstance(msg, AIMessage):
                                print(f"🔥🔥 AIMessage - has content: {bool(msg.content)}, content type: {type(msg.content)}, has tool_calls: {bool(getattr(msg, 'tool_calls', None))}", flush=True)
                                if msg.content:
                                    final_content = msg.content
                                    # 🔥🔥 DEBUG: 打印 LLM 原始输出
                                    print("=" * 80, flush=True)
                                    print("🔥🔥 FINAL LLM OUTPUT (Raw String):", flush=True)
                                    print("=" * 80, flush=True)
                                    print(final_content, flush=True)
                                    print("=" * 80, flush=True)
                                    sys.stdout.flush()
                                    logger.info(f"🔥🔥 FINAL LLM OUTPUT (length: {len(final_content)}): {final_content[:500]}...")
                                elif getattr(msg, 'tool_calls', None):
                                    print(f"🔥🔥 AIMessage has tool_calls but no content. Tool calls: {len(msg.tool_calls)}", flush=True)
                                    sys.stdout.flush()

                                # Extract SQL from tool calls
                                if msg.tool_calls:
                                    # 🔍 详细记录工具调用（用于诊断编造数据问题）
                                    logger.info(f"🔍 [AI工具调用] 共 {len(msg.tool_calls)} 个工具调用")
                                    for tc in msg.tool_calls:
                                        tool_name = tc.get("name", "unknown")
                                        tool_args = tc.get("args", {})
                                        logger.info(f"🔍 [AI工具调用] 工具: {tool_name}, 参数: {tool_args}")
                                        if verbose:
                                            logger.debug(f"AI tool call: {tool_name}")
                                        
                                        # Check if this is a chart tool call
                                        if "chart" in tool_name.lower() or "echarts" in tool_name.lower():
                                            if verbose:
                                                logger.info(f"Detected chart tool call: {tool_name}")
                                        
                                        if tc.get("name") in ("query", "execute_sql_safe"):
                                            executed_sql = tc.get("args", {}).get("query") or tc.get("args", {}).get("sql")

                            # Capture tool results
                            elif isinstance(msg, ToolMessage):
                                try:
                                    content = msg.content
                                    tool_name = getattr(msg, 'name', None) or 'unknown'
                                    
                                    # 🔍 详细记录工具调用结果（用于诊断编造数据问题）
                                    logger.info(f"🔍 [工具调用结果] 工具名: {tool_name}")
                                    logger.info(f"🔍 [工具调用结果] 内容类型: {type(content)}")
                                    if isinstance(content, str):
                                        content_preview = content[:500] if len(content) > 500 else content
                                        logger.info(f"🔍 [工具调用结果] 内容预览: {content_preview}")
                                        # 检查是否包含错误信息
                                        if "错误" in content or "Error" in content or "失败" in content:
                                            logger.warning(f"⚠️ [工具调用结果] 工具返回了错误信息: {content[:200]}")
                                    else:
                                        logger.info(f"🔍 [工具调用结果] 内容: {str(content)[:500]}")
                                    
                                    # Log tool message for debugging
                                    if verbose:
                                        logger.debug(f"Received ToolMessage from tool: {tool_name}, content type: {type(content)}")
                                    
                                    # Check if this is a chart tool result (MCP ECharts)
                                    # MCP ECharts tools typically return content with image data
                                    if isinstance(content, str):
                                        if verbose:
                                            logger.debug(f"ToolMessage content (first 200 chars): {content[:200]}")
                                        # Try to parse as JSON first
                                        try:
                                            parsed_content = json.loads(content)
                                            
                                            # Check if it's a list of content items (MCP format)
                                            if isinstance(parsed_content, list):
                                                for item in parsed_content:
                                                    if isinstance(item, dict):
                                                        # Check for image type content
                                                        if item.get("type") == "image" and item.get("data"):
                                                            # Extract Base64 image data
                                                            image_data = item.get("data")
                                                            # Ensure it's a data URI
                                                            if isinstance(image_data, str):
                                                                if image_data.startswith("data:"):
                                                                    chart_image = image_data
                                                                elif image_data.startswith("http"):
                                                                    chart_image = image_data
                                                                else:
                                                                    # Assume it's base64 without prefix
                                                                    chart_image = f"data:image/png;base64,{image_data}"
                                                            logger.info(f"Extracted chart image from MCP tool result (length: {len(chart_image) if chart_image else 0})")
                                                        # Also check for text content that might be a URL
                                                        elif item.get("type") == "text" and isinstance(item.get("text"), str):
                                                            text = item.get("text")
                                                            if text.startswith("http") and not chart_image:
                                                                chart_image = text
                                                                logger.info(f"Extracted chart URL from MCP tool result: {chart_image}")
                                            # If it's a dict, check for image fields
                                            elif isinstance(parsed_content, dict):
                                                if parsed_content.get("type") == "image" and parsed_content.get("data"):
                                                    image_data = parsed_content.get("data")
                                                    if isinstance(image_data, str):
                                                        if image_data.startswith("data:"):
                                                            chart_image = image_data
                                                        elif image_data.startswith("http"):
                                                            chart_image = image_data
                                                        else:
                                                            chart_image = f"data:image/png;base64,{image_data}"
                                                    logger.info(f"Extracted chart image from MCP tool result (dict format)")
                                                elif parsed_content.get("url") and not chart_image:
                                                    chart_image = parsed_content.get("url")
                                                    logger.info(f"Extracted chart URL from MCP tool result: {chart_image}")
                                            else:
                                                # Fallback: treat as query results
                                                query_results = parsed_content
                                        except json.JSONDecodeError:
                                            # Not JSON, might be plain text or other format
                                            # Check if it looks like a URL
                                            if content.startswith("http") and not chart_image:
                                                chart_image = content
                                                logger.info(f"Extracted chart URL from tool result: {chart_image}")
                                            else:
                                                query_results = content
                                    else:
                                        # Content is not a string, check if it's a dict/list with image data
                                        if isinstance(content, list):
                                            for item in content:
                                                if isinstance(item, dict) and item.get("type") == "image" and item.get("data"):
                                                    image_data = item.get("data")
                                                    if isinstance(image_data, str):
                                                        if image_data.startswith("data:"):
                                                            chart_image = image_data
                                                        elif image_data.startswith("http"):
                                                            chart_image = image_data
                                                        else:
                                                            chart_image = f"data:image/png;base64,{image_data}"
                                                    logger.info(f"Extracted chart image from MCP tool result (list format)")
                                        elif isinstance(content, dict):
                                            if content.get("type") == "image" and content.get("data"):
                                                image_data = content.get("data")
                                                if isinstance(image_data, str):
                                                    if image_data.startswith("data:"):
                                                        chart_image = image_data
                                                    elif image_data.startswith("http"):
                                                        chart_image = image_data
                                                    else:
                                                        chart_image = f"data:image/png;base64,{image_data}"
                                                logger.info(f"Extracted chart image from MCP tool result (dict format)")
                                            elif content.get("url") and not chart_image:
                                                chart_image = content.get("url")
                                                logger.info(f"Extracted chart URL from MCP tool result: {chart_image}")
                                            else:
                                                query_results = content
                                        else:
                                            query_results = content
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"Failed to parse tool message content: {e}")
                                    query_results = msg.content
        except BaseException as stream_error:
            # Catch TaskGroup and other stream errors (including ExceptionGroup)
            logger.error(f"Agent stream execution failed: {stream_error}", exc_info=True)
            
            # Extract more detailed error message
            error_msg = str(stream_error)
            detailed_errors = []
            
            # Handle ExceptionGroup (Python 3.11+) - TaskGroup errors are ExceptionGroup
            if hasattr(stream_error, "exceptions") and stream_error.exceptions:
                # This is an ExceptionGroup - extract all sub-exceptions with full traceback
                logger.error(f"ExceptionGroup detected with {len(stream_error.exceptions)} sub-exception(s)")
                
                for idx, exc in enumerate(stream_error.exceptions):
                    # Print full traceback for each sub-exception to console
                    exc_type = type(exc)
                    exc_value = exc
                    exc_traceback = getattr(exc, "__traceback__", None)
                    
                    # Print to console for immediate visibility
                    print(f"\n{'='*80}")
                    print(f"Sub-exception {idx + 1}/{len(stream_error.exceptions)}:")
                    print(f"{'='*80}")
                    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None)
                    print(f"{'='*80}\n")
                    
                    # Also log to logger
                    exc_str = str(exc)
                    if exc_traceback:
                        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                        logger.error(f"Sub-exception {idx + 1} full traceback:\n{tb_str}")
                    else:
                        logger.error(f"Sub-exception {idx + 1}: {exc_type.__name__}: {exc_str}")
                    
                    # Try to get more details from the exception
                    if hasattr(exc, "__cause__") and exc.__cause__:
                        exc_str = f"{exc_str} (原因: {exc.__cause__})"
                    
                    detailed_errors.append(exc_str)
                
                error_msg = f"Agent执行失败: {', '.join(detailed_errors)}"
            elif "TaskGroup" in error_msg or "sub-exception" in error_msg:
                # Try to get the underlying exception with more details
                logger.error(f"TaskGroup error detected. Exception type: {type(stream_error)}, has __cause__: {hasattr(stream_error, '__cause__')}, has __context__: {hasattr(stream_error, '__context__')}, has exceptions: {hasattr(stream_error, 'exceptions')}")
                
                # Print full traceback to console
                print(f"\n{'='*80}")
                print("TaskGroup Error Full Traceback:")
                print(f"{'='*80}")
                traceback.print_exception(type(stream_error), stream_error, stream_error.__traceback__, limit=None)
                print(f"{'='*80}\n")
                
                # Check __cause__
                if hasattr(stream_error, "__cause__") and stream_error.__cause__:
                    cause_str = str(stream_error.__cause__)
                    logger.error(f"Found __cause__: {type(stream_error.__cause__)} - {cause_str}")
                    
                    # If the cause is also an ExceptionGroup, extract its exceptions
                    if hasattr(stream_error.__cause__, "exceptions"):
                        print(f"\n{'='*80}")
                        print("ExceptionGroup in __cause__:")
                        print(f"{'='*80}")
                        for idx, exc in enumerate(stream_error.__cause__.exceptions):
                            print(f"\nSub-exception {idx + 1}/{len(stream_error.__cause__.exceptions)}:")
                            traceback.print_exception(type(exc), exc, getattr(exc, "__traceback__", None), limit=None)
                        print(f"{'='*80}\n")
                        
                        for exc in stream_error.__cause__.exceptions:
                            exc_detail = str(exc)
                            logger.error(f"Extracted sub-exception from __cause__: {type(exc)} - {exc_detail}")
                            detailed_errors.append(exc_detail)
                    else:
                        detailed_errors.append(cause_str)
                
                # Check __context__
                if hasattr(stream_error, "__context__") and stream_error.__context__:
                    context_str = str(stream_error.__context__)
                    logger.error(f"Found __context__: {type(stream_error.__context__)} - {context_str}")
                    if context_str not in detailed_errors:
                        detailed_errors.append(context_str)
                
                # Check if the exception itself has useful attributes
                if hasattr(stream_error, "args") and stream_error.args:
                    for arg in stream_error.args:
                        if isinstance(arg, Exception):
                            arg_str = str(arg)
                            logger.error(f"Found exception in args: {type(arg)} - {arg_str}")
                            detailed_errors.append(arg_str)
                
                # Log full traceback to logger
                tb_str = ''.join(traceback.format_exception(type(stream_error), stream_error, stream_error.__traceback__))
                logger.error(f"Full traceback:\n{tb_str}")
                
                if detailed_errors:
                    error_msg = f"Agent执行失败: {'; '.join(detailed_errors)}"
                    logger.error(f"Extracted detailed errors: {detailed_errors}")
                else:
                    # Fallback: log the full exception details and provide a generic message
                    logger.error(f"Could not extract detailed error from TaskGroup. Full error: {stream_error}", exc_info=True)
                    error_msg = "Agent执行过程中发生错误，可能是工具执行失败或数据库连接问题。请检查数据源配置和数据库连接状态。详细错误信息已记录到日志。"
            
            raise Exception(error_msg) from stream_error

        # Extract ECharts JSON configuration from LLM response
        # Look for [CHART_START]...{...}[CHART_END] pattern in final_content
        echarts_option_from_text = None
        # 🔥🔥 DEBUG: 在解析前再次打印最终内容
        print("=" * 80)
        print("🔥🔥 FINAL CONTENT BEFORE PARSING:")
        print("=" * 80)
        print(final_content)
        print("=" * 80)
        logger.info(f"🔥🔥 FINAL CONTENT BEFORE PARSING (length: {len(final_content)}): {final_content[:500]}...")
        
        cleaned_content = final_content
        
        if final_content:
            chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
            match = re.search(chart_pattern, final_content)
            
            # 🔥🔥 DEBUG: 打印匹配结果
            if match:
                print("=" * 80)
                print("🔥🔥 CHART PATTERN MATCHED!")
                print(f"🔥🔥 Matched JSON string (first 500 chars): {match.group(1)[:500]}")
                print("=" * 80)
                logger.info(f"🔥🔥 CHART PATTERN MATCHED! JSON string length: {len(match.group(1))}")
            else:
                print("=" * 80)
                print("🔥🔥 CHART PATTERN NOT FOUND IN FINAL CONTENT!")
                print("=" * 80)
                logger.warning("🔥🔥 CHART PATTERN NOT FOUND IN FINAL CONTENT!")
            
            if match:
                json_str = match.group(1).strip()
                try:
                    echarts_option_from_text = json.loads(json_str)
                    logger.info("✅ Successfully extracted ECharts JSON configuration from LLM response")
                    
                    # Remove the chart configuration from text content to avoid displaying raw JSON
                    cleaned_content = re.sub(chart_pattern, '', final_content).strip()
                    logger.debug(f"Removed chart configuration from text content. Original length: {len(final_content)}, Cleaned length: {len(cleaned_content)}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"⚠️ Failed to parse ECharts JSON configuration from LLM response: {e}. "
                        f"JSON string: {json_str[:200]}..."
                    )
                    # Keep original content if parsing fails
                    cleaned_content = final_content
            else:
                # No chart configuration found, keep original content
                cleaned_content = final_content

        # 🔥 第一步修复：SQL 提取兜底逻辑（被动触发）
        # 检查是否有 tool_calls 但没有执行 SQL
        has_tool_calls = False
        for msg in all_messages:
            if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
                has_tool_calls = True
                break
        
        # 如果 tool_calls 为空，但文本内容中包含 SQL 代码块，强制提取并执行
        if not executed_sql and final_content:
            # 尝试从 markdown 代码块中提取 SQL
            # 匹配 ```sql ... ``` 格式
            sql_patterns = [
                r'```sql\s*\n(.*?)\n```',  # 标准格式：```sql\n...\n```
                r'```sql\n(.*?)\n```',     # 紧凑格式
                r'```sql(.*?)```',         # 无换行格式
                r'```\s*sql\s*\n(.*?)\n```',  # 带空格的格式
            ]
            
            for pattern in sql_patterns:
                match = re.search(pattern, final_content, re.DOTALL | re.IGNORECASE)
                if match:
                    extracted_sql = match.group(1).strip()
                    # 验证提取的 SQL 看起来合理（至少包含 SELECT）
                    if extracted_sql and ('SELECT' in extracted_sql.upper() or 'WITH' in extracted_sql.upper()):
                        executed_sql = extracted_sql
                        logger.warning(f"⚠️ Detected raw SQL in text (no tool call), forcing execution... SQL: {executed_sql[:100]}...")
                        break
            
            # 如果还是没找到，尝试更宽松的模式（查找包含 SELECT 的代码块）
            if not executed_sql:
                # 匹配任何包含 SQL 关键字的代码块
                loose_pattern = r'```(?:sql|SQL)?\s*\n((?:SELECT|WITH|INSERT|UPDATE|DELETE).*?)\n```'
                match = re.search(loose_pattern, final_content, re.DOTALL | re.IGNORECASE)
                if match:
                    extracted_sql = match.group(1).strip()
                    if extracted_sql:
                        executed_sql = extracted_sql
                        logger.warning(f"⚠️ Detected raw SQL in text (loose pattern), forcing execution... SQL: {extracted_sql[:100]}...")
            
            # 如果没有找到 SQL 代码块，检查是否在普通文本中有 SQL 语句
            if not executed_sql:
                # 查找以 SELECT/WITH 开头的文本行（可能是直接写的 SQL）
                sql_line_pattern = r'(?:^|\n)((?:SELECT|WITH)\s+[^`]+?)(?:\n|$)'
                match = re.search(sql_line_pattern, final_content, re.IGNORECASE | re.MULTILINE)
                if match:
                    potential_sql = match.group(1).strip()
                    # 验证这看起来像 SQL（包含常见关键字）
                    if len(potential_sql) > 20 and any(kw in potential_sql.upper() for kw in ['FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY']):
                        executed_sql = potential_sql
                        logger.warning(f"⚠️ Detected SQL-like text (no code block), forcing execution... SQL: {executed_sql[:100]}...")
            
            if not executed_sql:
                logger.warning(f"⚠️ 无法从 tool_calls 或文本内容中提取 SQL。final_content 长度: {len(final_content)}, has_tool_calls: {has_tool_calls}")

        # 🔥 关键修复：检查文件数据源是否调用了必要的工具
        # 如果 database_url 是文件类型（file://开头或容器内绝对路径），但LLM没有调用 inspect_file 或 analyze_dataframe，强制返回错误
        logger.info(f"🔍 [文件数据源检查] 开始检查 - database_url类型: {type(database_url)}, database_url值: {database_url}")
        
        # 🔧 改进：支持多种文件路径格式
        is_file_datasource = False
        if database_url:
            # 检查是否是文件路径格式
            is_file_datasource = (
                database_url.startswith("file://") or  # MinIO路径格式
                database_url.startswith("/app/uploads/") or  # 容器内绝对路径
                database_url.startswith("/app/data/") or  # 容器内数据路径
                database_url.endswith((".xlsx", ".xls", ".csv")) or  # 直接以扩展名结尾
                ".xlsx" in database_url or ".xls" in database_url or ".csv" in database_url  # 路径中包含扩展名
            )
        
        logger.info(f"🔍 [文件数据源检查] database_url: {database_url}, is_file_datasource: {is_file_datasource}, final_content长度: {len(final_content) if final_content else 0}")
        
        if is_file_datasource:
            # 检查是否调用了文件工具
            has_inspect_file = False
            has_analyze_dataframe = False
            logger.info(f"🔍 [文件数据源检查] 开始检查工具调用，all_messages 数量: {len(all_messages)}")
            for msg in all_messages:
                if isinstance(msg, AIMessage):
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if tool_calls:
                        logger.info(f"🔍 [文件数据源检查] 找到 AIMessage 包含 tool_calls: {len(tool_calls)} 个")
                        for tc in tool_calls:
                            # 处理不同的 tool_calls 格式
                            if isinstance(tc, dict):
                                tool_name = tc.get("name", "").lower()
                            elif hasattr(tc, 'name'):
                                tool_name = str(tc.name).lower()
                            else:
                                tool_name = str(tc).lower()
                            logger.info(f"🔍 [文件数据源检查] 工具名称: {tool_name}")
                            if "inspect_file" in tool_name or "get_column_info" in tool_name:
                                has_inspect_file = True
                                logger.info(f"✅ [文件数据源检查] 检测到 inspect_file 调用")
                            if "analyze_dataframe" in tool_name or "python_interpreter" in tool_name:
                                has_analyze_dataframe = True
                                logger.info(f"✅ [文件数据源检查] 检测到 analyze_dataframe 调用")
            logger.info(f"🔍 [文件数据源检查] 工具调用状态 - inspect_file: {has_inspect_file}, analyze_dataframe: {has_analyze_dataframe}")
            
            # 🔧 改进：更严格的检查逻辑
            # 如果LLM没有调用必要的文件工具，但生成了答案，强制返回错误
            logger.info(f"🔍 [文件数据源检查] 检查条件 - has_inspect_file: {has_inspect_file}, has_analyze_dataframe: {has_analyze_dataframe}, final_content长度: {len(final_content) if final_content else 0}")
            
            # 🚨 关键修复：如果没有任何工具调用，且生成了答案，直接判定为幻觉
            if not has_inspect_file and not has_analyze_dataframe:
                if final_content and len(final_content.strip()) > 50:  # 如果生成了较长的答案
                    # 检查答案中是否包含数据（如用户名称列表、统计数据等），如果是，说明是幻觉数据
                    # 扩展可疑关键词列表，包含更多常见的测试数据
                    suspicious_keywords = [
                        # 中文测试数据（扩展列表）
                        "张三", "李四", "王五", "赵六", "钱七", "孙七", "周八", "吴九", "郑十",
                        # 英文测试数据
                        "John Doe", "Jane Smith", "Bob Johnson", "Alice", "Bob", "Charlie", 
                        "David", "Eve", "Frank", "Grace", "Henry", "Irene", "Jack",
                        # 其他常见测试名字
                        "Test User", "Sample User", "Demo User",
                        # 常见的幻觉数据模式
                        "平均消费金额", "VIP 等级", "order_id", "user_id", "product_id"
                    ]
                    has_suspicious_data = any(keyword in final_content for keyword in suspicious_keywords)
                    
                    # 更严格的检查：如果包含数据相关的关键词，且没有调用工具
                    is_data_query = (
                        ("用户" in final_content and "名称" in final_content) or 
                        ("users" in final_content.lower() and "name" in final_content.lower()) or
                        ("列名" in final_content or "工作表" in final_content) or
                        ("列" in final_content and "统计" in final_content) or
                        ("VIP" in final_content and "等级" in final_content) or
                        ("平均" in final_content and "金额" in final_content)
                    )
                    
                    # 🚨 关键修复：如果生成了答案但没有调用工具，直接判定为幻觉
                    if has_suspicious_data or is_data_query or len(final_content) > 200:
                        logger.error(f"🚨 [文件数据源检查] LLM没有调用文件工具但生成了答案，疑似幻觉数据！")
                        logger.error(f"   调用了 inspect_file: {has_inspect_file}, 调用了 analyze_dataframe: {has_analyze_dataframe}")
                        logger.error(f"   答案内容预览: {final_content[:500]}...")
                        logger.error(f"   包含可疑关键词: {has_suspicious_data}, 是数据查询: {is_data_query}, 答案长度: {len(final_content)}")
                        # 强制返回错误
                        cleaned_content = "无法读取数据文件，请检查上传路径。系统检测到未调用必要的文件工具（inspect_file 或 analyze_dataframe），无法验证数据真实性。请确保文件已正确上传。"
                        final_content = cleaned_content
                        query_results = None
                    else:
                        logger.warning(f"⚠️ [文件数据源检查] LLM没有调用文件工具，但答案看起来不是数据查询，暂不拦截")
                else:
                    logger.info(f"ℹ️ [文件数据源检查] LLM没有调用文件工具，但也没有生成答案或答案很短，暂不拦截")
            else:
                logger.info(f"✅ [文件数据源检查] LLM已调用必要的文件工具，检查通过")

        # 🔥 关键修复：如果LLM没有执行SQL查询，但提供了SQL（无论是通过工具调用还是文本），强制执行它
        if not query_results and executed_sql:
            logger.warning(f"⚠️ LLM提供了SQL但没有执行查询（或查询未返回结果），强制自动执行SQL...")
            try:
                # 使用execute_sql_safe工具执行SQL（这是安全的SQL执行工具）
                from .tools import execute_sql_safe
                
                # 执行SQL查询
                logger.info(f"🔄 正在执行提取的 SQL: {executed_sql[:200]}...")
                result = execute_sql_safe.invoke({"sql": executed_sql, "query": executed_sql})
                
                # 解析结果
                if isinstance(result, str):
                    try:
                        query_results = json.loads(result)
                        logger.info(f"✅ SQL执行成功，返回JSON格式结果，包含 {len(query_results) if isinstance(query_results, list) else 1} 条记录")
                    except json.JSONDecodeError:
                        # 如果不是JSON，可能是错误信息或纯文本结果
                        logger.warning(f"SQL执行返回非JSON结果: {result[:200]}...")
                        # 尝试将字符串结果包装为列表
                        query_results = [{"result": result}] if result else None
                elif isinstance(result, list):
                    query_results = result
                    logger.info(f"✅ SQL执行成功，返回列表格式结果，包含 {len(query_results)} 条记录")
                elif isinstance(result, dict):
                    query_results = [result]
                    logger.info(f"✅ SQL执行成功，返回字典格式结果")
                else:
                    query_results = None
                    logger.warning(f"SQL执行返回未知格式: {type(result)}")
                
                if query_results:
                    logger.info(f"✅ 成功自动执行SQL查询，获取到 {len(query_results) if isinstance(query_results, list) else 1} 条结果")
                else:
                    logger.warning("⚠️ 自动执行SQL查询但没有获取到结果")
            except Exception as e:
                logger.error(f"❌ 尝试自动执行SQL时出错: {e}", exc_info=True)
                # 即使执行失败，也继续处理，至少可以显示SQL和错误信息

        # Build VisualizationResponse
        query_result = QueryResult()
        chart_config = ChartConfig()
        echarts_option = None

        if query_results and isinstance(query_results, list):
            query_result = QueryResult.from_raw_data(query_results)

            # Auto-infer chart type and prepare config with ECharts option
            if executed_sql:
                # 从用户问题中推断图表类型（优先）
                inferred_type = None
                question_lower = question.lower()
                if any(kw in question_lower for kw in ["趋势", "变化", "时间", "月份", "年度", "季度"]):
                    inferred_type = "line"
                elif any(kw in question_lower for kw in ["对比", "比较", "排名"]):
                    inferred_type = "bar"
                elif any(kw in question_lower for kw in ["占比", "分布", "比例"]):
                    inferred_type = "pie"
                
                # 生成图表标题（从问题中提取或使用默认值）
                chart_title = "查询结果"
                if "收入" in question:
                    chart_title = "收入趋势分析" if inferred_type == "line" else "收入分析"
                elif "销售" in question:
                    chart_title = "销售趋势分析" if inferred_type == "line" else "销售分析"
                elif "趋势" in question:
                    chart_title = "趋势分析"
                
                _, chart_config, echarts_option = prepare_mcp_chart_request(
                    sql_result=query_results,
                    sql=executed_sql,
                    title=chart_title,
                    chart_type=inferred_type,
                    question=question
                )
        
        # Prefer ECharts option from LLM text response over auto-generated one
        if echarts_option_from_text:
            echarts_option = echarts_option_from_text
            logger.info("Using ECharts configuration from LLM text response")
        elif echarts_option:
            logger.info("Using auto-generated ECharts configuration")
        elif query_results and isinstance(query_results, list) and len(query_results) > 0:
            # 如果LLM没有生成图表配置，但有查询结果，强制生成一个基础图表配置
            logger.warning("LLM did not generate chart configuration, but query results exist. Auto-generating chart...")
            try:
                # 从问题中推断图表类型
                question_lower = question.lower()
                inferred_type = "table"
                if any(kw in question_lower for kw in ["趋势", "变化", "时间", "月份", "年度", "季度"]):
                    inferred_type = "line"
                elif any(kw in question_lower for kw in ["对比", "比较", "排名"]):
                    inferred_type = "bar"
                elif any(kw in question_lower for kw in ["占比", "分布", "比例"]):
                    inferred_type = "pie"
                
                # 生成图表标题
                chart_title = "查询结果"
                if "收入" in question:
                    chart_title = "收入趋势分析" if inferred_type == "line" else "收入分析"
                elif "销售" in question:
                    chart_title = "销售趋势分析" if inferred_type == "line" else "销售分析"
                elif "趋势" in question:
                    chart_title = "趋势分析"
                
                # 自动生成图表配置
                _, chart_config, echarts_option = prepare_mcp_chart_request(
                    sql_result=query_results,
                    sql=executed_sql or "",
                    title=chart_title,
                    chart_type=inferred_type,
                    question=question
                )
                logger.info(f"Auto-generated chart configuration: type={inferred_type}, title={chart_title}")
            except Exception as e:
                logger.error(f"Failed to auto-generate chart configuration: {e}", exc_info=True)

        # Add chart image if extracted from MCP tool call
        if chart_image:
            chart_config.chart_image = chart_image
            logger.info(
                f"✅ Successfully extracted chart_image from MCP tool call. "
                f"Type: {type(chart_image)}, "
                f"Length: {len(chart_image) if isinstance(chart_image, str) else 'N/A'}, "
                f"Preview: {chart_image[:50] if isinstance(chart_image, str) else 'N/A'}..."
            )
        elif enable_echarts and chart_config.chart_type.value != "table":
            # Chart generation was enabled but no image was extracted
            # This could mean:
            # 1. MCP ECharts service is not available
            # 2. Chart tool was not called by the agent
            # 3. Chart tool call failed silently
            logger.warning(
                f"⚠️ Chart generation enabled but no chart_image extracted. "
                f"Chart type: {chart_config.chart_type.value}, "
                f"enable_echarts: {enable_echarts}. "
                f"This may indicate MCP ECharts service is unavailable or chart tool call failed. "
                f"All messages count: {len(all_messages)}"
            )
            # Log all tool messages for debugging
            tool_messages = [m for m in all_messages if isinstance(m, ToolMessage)]
            logger.debug(f"Tool messages found: {len(tool_messages)}")
            for i, tm in enumerate(tool_messages):
                tool_name = getattr(tm, 'name', None) or 'unknown'
                content_preview = str(tm.content)[:100] if hasattr(tm, 'content') else 'N/A'
                logger.debug(f"  ToolMessage {i+1}: name={tool_name}, content_preview={content_preview}")
            # Don't set chart_image to None explicitly - let it remain None
            # Frontend will handle missing chart_image gracefully

        # 🔴 第一道防线：检测工具调用失败
        tool_error_detected = False
        tool_calls_info = []
        
        # 检查所有工具消息，看是否有SYSTEM ERROR
        for msg in all_messages:
            if isinstance(msg, ToolMessage):
                content = msg.content
                tool_name = getattr(msg, 'name', None) or 'unknown'
                if isinstance(content, str) and 'SYSTEM ERROR' in content:
                    tool_error_detected = True
                    tool_calls_info.append({
                        "name": tool_name,
                        "status": "error",
                        "error": "工具执行失败或返回空数据"
                    })
                    logger.warning(f"⚠️ [第一道防线] 检测到工具调用失败: {tool_name}")
                elif isinstance(content, str) and ('错误' in content or 'Error' in content or '失败' in content):
                    # 检查是否是错误信息（但不是SYSTEM ERROR）
                    tool_calls_info.append({
                        "name": tool_name,
                        "status": "error",
                        "error": content[:100]
                    })
                else:
                    tool_calls_info.append({
                        "name": tool_name,
                        "status": "success"
                    })
        
        # 检查最终回答中是否包含SYSTEM ERROR
        if cleaned_content and 'SYSTEM ERROR' in cleaned_content:
            tool_error_detected = True
            logger.warning("⚠️ [第一道防线] 最终回答中包含SYSTEM ERROR")

        response = VisualizationResponse(
            answer=cleaned_content or "",  # Use cleaned content without JSON configuration
            sql=executed_sql or "",
            data=query_result,
            chart=chart_config,
            echarts_option=echarts_option,
            success=True,
            error=None,
        )

        # Return both dict (backward compatible) and response object
        return {
            "answer": cleaned_content,  # Use cleaned content
            "sql": executed_sql,
            "data": query_results,
            "success": True,
            "error": None,
            "response": response,  # V5.1: structured response
            # 🔴 第三道防线：添加工具调用状态信息供前端使用
            "metadata": {
                "tool_error": tool_error_detected,
                "tool_status": "error" if tool_error_detected else "success",
                "tool_calls": tool_calls_info,
                "reasoning": None  # 可以在这里添加推理过程
            }
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        error_response = VisualizationResponse(
            success=False,
            error=str(e),
        )
        return {
            "answer": None,
            "sql": None,
            "data": None,
            "success": False,
            "error": str(e),
            "response": error_response,  # V5.1: structured response
        }


# ============================================================
# Convenience Functions
# ============================================================

async def ask(
    question: str,
    database_url: str = None,
    thread_id: str = "default",
) -> str:
    """
    Simple interface to ask the agent a question.

    Args:
        question: Natural language question
        database_url: Database connection (uses settings if not provided)
        thread_id: Session ID

    Returns:
        Agent's text response
    """
    db_url = database_url or getattr(settings, 'database_url', '')

    if not db_url:
        return "Error: No database URL configured"

    result = await run_agent(
        question=question,
        database_url=db_url,
        thread_id=thread_id,
    )

    if result["success"]:
        return result["answer"]
    else:
        return f"Error: {result['error']}"


def get_agent_status() -> Dict[str, Any]:
    """
    Get current agent status for health checks.

    Returns:
        Status dictionary
    """
    return {
        "initialized": _cached_agent is not None,
        "tools_loaded": len(_cached_tools),
        "mcp_connected": _cached_mcp_client is not None,
        "recursion_limit": MAX_RECURSION_LIMIT,
    }


# ============================================================
# API Interface
# ============================================================

async def run_agent_for_api(
    request: AgentRequest,
    database_url: str = None,
) -> Dict[str, Any]:
    """
    Run agent and return formatted API response.

    This is the main entry point for API endpoints.

    Args:
        request: AgentRequest with query and options
        database_url: Database connection (uses settings if not provided)

    Returns:
        Formatted API response dictionary with:
        - success: bool
        - answer: str
        - sql: str
        - table: dict with columns, rows, row_count
        - chart: dict with type, labels, values
        - echarts_option: dict for frontend rendering
        - error: str or None
    """
    db_url = database_url or request.database_url or getattr(settings, 'database_url', '')

    if not db_url:
        return format_error_response("No database URL configured")

    try:
        result = await run_agent(
            question=request.query,
            database_url=db_url,
            thread_id=request.session_id or "default",
            # 鎭㈠鍥捐〃鐢熸垚鍔熻兘锛屾寜璇锋眰鍙傛暟鍐冲畾鏄惁寮€鍚?ECharts MCP
            enable_echarts=request.generate_chart,
        )

        if result["success"] and "response" in result:
            return format_api_response(result["response"])
        elif result["success"]:
            # Fallback for old format
            return {
                "success": True,
                "answer": result.get("answer", ""),
                "sql": result.get("sql", ""),
                "table": {
                    "columns": [],
                    "rows": result.get("data", []) if isinstance(result.get("data"), list) else [],
                    "row_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else 0,
                    "truncated": False
                },
                "chart": None,
                "echarts_option": None,
                "error": None
            }
        else:
            return format_error_response(result.get("error", "Unknown error"), result.get("sql", ""))

    except Exception as e:
        logger.error(f"API agent execution failed: {e}", exc_info=True)
        return format_error_response(str(e))


# ============================================================
# Export for __init__.py
# ============================================================

__all__ = [
    "build_agent",
    "run_agent",
    "run_agent_for_api",
    "reset_agent",
    "ask",
    "get_agent_status",
    "create_llm",
    "get_mcp_config",
    "MAX_RECURSION_LIMIT",
    "AgentRequest",
    "VisualizationResponse",
]
