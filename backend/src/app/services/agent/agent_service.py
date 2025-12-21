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
    inspect_file,
)
from .examples import load_golden_examples

# Import V5.1 visualization modules
from .models import VisualizationResponse, QueryResult, ChartConfig
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

# Context Management Configuration
MAX_CONTEXT_TOKENS = 120000  # 留出一些余量，避免超过131072限制
MAX_MESSAGE_HISTORY = 20  # 最多保留最近20条消息
MAX_TOOL_RESULT_LENGTH = 5000  # 工具返回结果最大长度（字符数）


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
                # 确保tool_input不为None（某些工具需要dict参数）
                if tool_input is None:
                    tool_input = {}
                if hasattr(tool, "ainvoke"):
                    try:
                        # 🔥 修复：改进事件循环检测逻辑
                        try:
                            # 尝试获取当前事件循环
                            loop = asyncio.get_running_loop()  # 使用get_running_loop而不是get_event_loop
                            # 如果成功获取到运行中的循环，使用run_coroutine_threadsafe
                            import concurrent.futures
                            future = asyncio.run_coroutine_threadsafe(
                                tool.ainvoke(tool_input, **kwargs), 
                                loop
                            )
                            return future.result(timeout=30)
                        except RuntimeError:
                            # 如果没有运行中的事件循环，尝试获取或创建
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # 如果事件循环正在运行，使用 run_coroutine_threadsafe
                                    import concurrent.futures
                                    future = asyncio.run_coroutine_threadsafe(
                                        tool.ainvoke(tool_input, **kwargs), 
                                        loop
                                    )
                                    return future.result(timeout=30)
                                else:
                                    # 如果事件循环未运行，直接运行
                                    return asyncio.run(tool.ainvoke(tool_input, **kwargs))
                            except RuntimeError:
                                # 如果完全没有事件循环，创建新的
                                return asyncio.run(tool.ainvoke(tool_input, **kwargs))
                    except RuntimeError as e:
                        # 如果asyncio.run失败（可能已经在事件循环中），尝试anyio
                        try:
                            return anyio.from_thread.run(tool.ainvoke, tool_input, **kwargs)
                        except BaseException as e2:
                            # Catch all exceptions including ExceptionGroup from anyio
                            error_msg = str(e2)
                            # Extract underlying exception if it's an ExceptionGroup
                            if hasattr(e2, "exceptions") and e2.exceptions:
                                # This is an ExceptionGroup (Python 3.11+)
                                underlying_errors = [str(exc) for exc in e2.exceptions]
                                error_msg = f"Tool execution failed: {', '.join(underlying_errors)}"
                            elif "TaskGroup" in error_msg or "sub-exception" in error_msg or "NoEventLoopError" in error_msg:
                                # Try to get more details from the exception
                                if hasattr(e2, "__cause__") and e2.__cause__:
                                    error_msg = f"Tool execution failed: {str(e2.__cause__)}"
                                else:
                                    error_msg = "Tool execution failed: 工具执行过程中发生错误（事件循环问题）"
                            logger.error(f"Tool execution failed in anyio.from_thread: {error_msg}", exc_info=True)
                            # Return error message instead of raising
                            return f"Error executing tool: {error_msg}"
                if hasattr(tool, "invoke"):
                    try:
                        result = tool.invoke(tool_input, **kwargs)
                        # 🔥 修复：确保工具输出始终是字符串，防止 API 400 错误
                        if not isinstance(result, str):
                            import json
                            try:
                                result = json.dumps(result, ensure_ascii=False, indent=2)
                            except (TypeError, ValueError):
                                result = str(result)
                        return result
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
                # 确保tool_input不为None（某些工具需要dict参数）
                if tool_input is None:
                    tool_input = {}
                if hasattr(tool, "ainvoke"):
                    try:
                        result = await tool.ainvoke(tool_input, **kwargs)
                        # 🔴 第一道防线：检查空数据
                        if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
                            logger.warning(f"⚠️ [第一道防线] 工具 {getattr(tool, 'name', 'unknown')} 返回空数据")
                            return 'SYSTEM ERROR: Tool execution failed or returned no data. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法获取数据，请检查数据源连接"。'
                        # 🔥 修复：确保工具输出始终是字符串，防止 API 400 错误
                        if not isinstance(result, str):
                            import json
                            try:
                                result = json.dumps(result, ensure_ascii=False, indent=2)
                            except (TypeError, ValueError):
                                result = str(result)
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
                        # 🔥 修复：确保工具输出始终是字符串，防止 API 400 错误
                        if not isinstance(result, str):
                            import json
                            try:
                                result = json.dumps(result, ensure_ascii=False, indent=2)
                            except (TypeError, ValueError):
                                result = str(result)
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
    # 🔥 修复：优先使用deepseek，只有在deepseek API密钥不存在时才回退
    # 回退优先级：OpenRouter > 智谱AI
    if provider == "deepseek":
        deepseek_api_key = api_key or getattr(settings, "DEEPSEEK_API_KEY", None) or getattr(settings, "deepseek_api_key", None)
        if not deepseek_api_key:
            # 优先检查OpenRouter
            if getattr(settings, "openrouter_api_key", None):
                logger.warning("⚠️ DeepSeek API密钥未配置，回退到OpenRouter")
                provider = "openrouter"
            # 其次检查智谱AI
            elif getattr(settings, "zhipuai_api_key", None):
                logger.warning("⚠️ DeepSeek API密钥未配置，回退到智谱AI")
                provider = "zhipu"
            else:
                logger.error("❌ DeepSeek API密钥未配置，且没有可用的回退Provider")
        else:
            logger.info("✅ 使用DeepSeek作为LLM Provider")

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
    # 🔥 修复：同时检查大写和小写的API密钥配置
    deepseek_api_key = api_key or getattr(settings, 'DEEPSEEK_API_KEY', None) or getattr(settings, 'deepseek_api_key', None) or ''
    return ChatOpenAI(
        model=model or getattr(settings, 'DEEPSEEK_MODEL', DEFAULT_MODEL),
        api_key=deepseek_api_key,
        base_url=base_url or getattr(settings, 'DEEPSEEK_BASE_URL', None) or getattr(settings, 'deepseek_base_url', 'https://api.deepseek.com'),
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
    
    Raises:
        RuntimeError: If npx command is not available
    """
    import shutil
    
    # Fix Windows npx command issue: use npx.cmd on Windows
    npx_command = "npx.cmd" if sys.platform == "win32" else "npx"
    
    # Check if npx is available
    npx_path = shutil.which(npx_command)
    if not npx_path:
        error_msg = (
            f"❌ npx 命令不可用。MCP PostgreSQL 服务器需要 Node.js/npm。\n"
            f"   请安装 Node.js 或设置 DISABLE_MCP_TOOLS=true 使用自定义工具。\n"
            f"   当前平台: {sys.platform}, 查找的命令: {npx_command}"
        )
        logger.error(error_msg)
        raise RuntimeError(
            f"npx command not found. Node.js is required for MCP servers. "
            f"Platform: {sys.platform}, Command: {npx_command}. "
            f"Set DISABLE_MCP_TOOLS=true to use custom tools instead."
        )
    
    logger.info(f"✅ npx 可用: {npx_path}")
    
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
                    # 首先尝试在当前事件循环中执行
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 如果事件循环正在运行，使用 run_coroutine_threadsafe
                            import concurrent.futures
                            future = asyncio.run_coroutine_threadsafe(
                                t.ainvoke(tool_input, **kwargs), 
                                loop
                            )
                            return future.result(timeout=30)
                        else:
                            # 如果事件循环未运行，直接运行
                            return asyncio.run(t.ainvoke(tool_input, **kwargs))
                    except RuntimeError:
                        # 如果没有事件循环，创建新的
                        return asyncio.run(t.ainvoke(tool_input, **kwargs))
                except RuntimeError:
                    # already in loop -> try anyio as fallback
                    try:
                        return anyio.from_thread.run(t.ainvoke, tool_input, **kwargs)
                    except Exception as e:
                        logger.error(f"Tool execution failed in _wrap_tool_for_langgraph: {e}", exc_info=True)
                        return f"Error executing tool: {str(e)}"
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
                        # 首先尝试在当前事件循环中执行
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 如果事件循环正在运行，使用 run_coroutine_threadsafe
                                import concurrent.futures
                                future = asyncio.run_coroutine_threadsafe(
                                    t.ainvoke(tool_input, **kwargs), 
                                    loop
                                )
                                result = future.result(timeout=30)
                            else:
                                # 如果事件循环未运行，直接运行
                                result = asyncio.run(t.ainvoke(tool_input, **kwargs))
                        except RuntimeError:
                            # 如果没有事件循环，创建新的
                            result = asyncio.run(t.ainvoke(tool_input, **kwargs))
                    except RuntimeError:
                        # already in loop -> try anyio as fallback
                        try:
                            result = anyio.from_thread.run(t.ainvoke, tool_input, **kwargs)
                        except Exception as e:
                            logger.error(f"Tool execution failed in _wrap_inspect_file_tool: {e}", exc_info=True)
                            result = f"Error executing tool: {str(e)}"
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
    
    # 跟踪已处理的工具，确保文件数据源工具总是可用
    processed_tool_names = set()

    for tool in mcp_tools:
        if tool.name == "query":
            # Replace with our secure wrapper
            logger.info("Replacing 'query' tool with secure execute_sql_safe")
            secure_tools.append(_wrap_tool_for_langgraph(execute_sql_safe))
            processed_tool_names.add("query")
        elif tool.name == "get_schema":
            secure_tools.append(_wrap_tool_for_langgraph(get_table_schema))
            processed_tool_names.add("get_schema")
        elif tool.name == "list_tables":
            secure_tools.append(_wrap_tool_for_langgraph(list_available_tables))
            processed_tool_names.add("list_tables")
        elif tool.name == "analyze_dataframe":
            # Replace with our custom version that handles MinIO file paths
            logger.info("Replacing 'analyze_dataframe' tool with custom MinIO-aware version")
            secure_tools.append(_wrap_tool_for_langgraph(analyze_dataframe))
            processed_tool_names.add("analyze_dataframe")
        elif tool.name == "inspect_file":
            # Replace with special wrapper that returns specific error message
            logger.info("Replacing 'inspect_file' tool with anti-hallucination wrapper")
            secure_tools.append(_wrap_inspect_file_tool(tool))
            processed_tool_names.add("inspect_file")
        else:
            # Pass through other tools (e.g., echarts, etc.)
            logger.info(f"Passing through tool: {tool.name}")
            secure_tools.append(_wrap_tool_for_langgraph(tool))
            processed_tool_names.add(tool.name)

    # 🔥 确保文件数据源工具总是可用（即使MCP服务器没有提供）
    if "inspect_file" not in processed_tool_names:
        logger.info("Adding 'inspect_file' tool (not provided by MCP server)")
        secure_tools.append(_wrap_inspect_file_tool(inspect_file))
    
    if "analyze_dataframe" not in processed_tool_names:
        logger.info("Adding 'analyze_dataframe' tool (not provided by MCP server)")
        secure_tools.append(_wrap_tool_for_langgraph(analyze_dataframe))

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
    disable_tools = os.getenv("DISABLE_MCP_TOOLS", "false").lower() == "true"
    
    if disable_tools:
        logger.info("⚠️ MCP 工具已禁用，将使用自定义工具")
        mcp_config = None
        _cached_mcp_client = None
    else:
        try:
            mcp_config = get_mcp_config(database_url, enable_echarts)
            logger.info(f"✅ MCP 配置已创建: {list(mcp_config.keys())}")
        except RuntimeError as e:
            # npx 不可用的情况
            logger.error(
                f"❌ MCP 配置创建失败: {e}\n"
                f"   提示: 设置 DISABLE_MCP_TOOLS=true 可以禁用 MCP 并使用自定义工具",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(f"❌ MCP 配置创建时发生未知错误: {e}", exc_info=True)
            raise
        
        _cached_mcp_client = MultiServerMCPClient(mcp_config)

    if not disable_tools:
        # Initialize MCP and get tools
        try:
            logger.info("🔄 正在初始化 MCP 工具...")
            raw_tools = await _cached_mcp_client.get_tools()
            logger.info(f"✅ MCP 工具加载成功，共 {len(raw_tools)} 个工具")
        except FileNotFoundError as e:
            # 处理 npx 或命令未找到的错误
            error_message = str(e)
            logger.error(
                f"❌ MCP 工具初始化失败：命令未找到\n"
                f"   错误信息: {error_message}\n"
                f"   可能原因: Node.js/npm 未安装或不在 PATH 中\n"
                f"   解决方案: 安装 Node.js 或设置 DISABLE_MCP_TOOLS=true",
                exc_info=True,
            )
            raise RuntimeError(
                f"MCP initialization failed: command not found. "
                f"Error: {error_message}. "
                f"Install Node.js or set DISABLE_MCP_TOOLS=true"
            ) from e
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
                    f"⚠️ MCP 工具加载失败，将尝试回退方案\n"
                    f"   错误类型: {error_type}\n"
                    f"   错误信息: {error_message}",
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

        # 🔥 注入文件数据源工具（如果MCP服务器没有提供）
        has_inspect_file = any(getattr(t, "name", "") == "inspect_file" for t in raw_tools)
        if not has_inspect_file:
            logger.warning("MCP server missing inspect_file; injecting fallback tool")
            raw_tools.append(inspect_file)

        has_analyze_dataframe = any(getattr(t, "name", "") == "analyze_dataframe" for t in raw_tools)
        if not has_analyze_dataframe:
            logger.warning("MCP server missing analyze_dataframe; injecting fallback tool")
            raw_tools.append(analyze_dataframe)

        # Wrap with security layer
        mcp_wrapper = MCPClientWrapper(_cached_mcp_client)
        # initialize with injected fallback tools
        await mcp_wrapper.initialize(raw_tools)
        set_mcp_client(mcp_wrapper)

        # Create secure tools
        _cached_tools = create_secure_tools(raw_tools)
        
        # 🔥 确保文件数据源工具总是可用（双重保险）
        tool_names = [getattr(t, "name", str(t)) for t in _cached_tools]
        if "inspect_file" not in tool_names:
            logger.warning("⚠️ inspect_file 工具未在 secure_tools 中找到，强制添加")
            _cached_tools.append(_wrap_inspect_file_tool(inspect_file))
        if "analyze_dataframe" not in tool_names:
            logger.warning("⚠️ analyze_dataframe 工具未在 secure_tools 中找到，强制添加")
            _cached_tools.append(_wrap_tool_for_langgraph(analyze_dataframe))
        
        # 记录最终的工具列表
        final_tool_names = [getattr(t, "name", str(t)) for t in _cached_tools]
        logger.info(
            f"✅ 最终工具列表已注册，共 {len(_cached_tools)} 个工具",
            extra={
                "tool_names": final_tool_names,
                "has_inspect_file": "inspect_file" in final_tool_names,
                "has_analyze_dataframe": "analyze_dataframe" in final_tool_names
            }
        )
    else:
        logger.warning("DISABLE_MCP_TOOLS=true, building agent without tools")
        _cached_tools = []

    # Create LLM with tools
    # 🔥 修复：强制优先使用DeepSeek，只有在DeepSeek API密钥不存在时才回退
    # 回退优先级：OpenRouter > 智谱AI
    preferred_provider = getattr(settings, "llm_provider", "deepseek")
    # 🔥 关键修复：如果配置了DeepSeek API密钥，强制使用DeepSeek，忽略llm_provider设置
    deepseek_api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or getattr(settings, "deepseek_api_key", None)
    if deepseek_api_key:
        preferred_provider = "deepseek"
        logger.info("✅ 检测到DeepSeek API密钥，强制使用DeepSeek作为LLM Provider")
    elif preferred_provider == "deepseek":
        # DeepSeek密钥未配置，但preferred_provider是deepseek，需要回退
        if getattr(settings, "openrouter_api_key", None):
            logger.info("⚠️ DeepSeek密钥未配置，但检测到OpenRouter密钥，回退到OpenRouter")
            preferred_provider = "openrouter"
        elif getattr(settings, "zhipuai_api_key", None):
            logger.info("⚠️ DeepSeek密钥未配置，但检测到智谱AI密钥，回退到智谱AI")
            preferred_provider = "zhipu"
    llm = create_llm(model=model, provider=preferred_provider)
    
    # 🔥 确保工具被正确绑定
    if _cached_tools:
        tool_names_for_binding = [getattr(t, "name", str(t)) for t in _cached_tools]
        logger.info(
            f"📦 准备绑定工具到 LLM，共 {len(_cached_tools)} 个工具",
            extra={
                "tool_names": tool_names_for_binding,
                "has_inspect_file": "inspect_file" in tool_names_for_binding,
                "has_analyze_dataframe": "analyze_dataframe" in tool_names_for_binding
            }
        )
        llm_with_tools = llm.bind_tools(_cached_tools)
        logger.info("✅ 工具已成功绑定到 LLM")
    else:
        logger.warning("⚠️ 没有工具可绑定，LLM 将无法调用工具")
        llm_with_tools = llm

    # Get system prompt with golden examples
    system_prompt = get_system_prompt()

    # Define agent node
    async def call_model(state: MessagesState) -> Dict[str, List]:
        messages = state["messages"]

        # 🔥 上下文管理：截断工具返回的大数据
        truncated_messages = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                # 截断工具返回的大数据
                content = msg.content
                if isinstance(content, str) and len(content) > MAX_TOOL_RESULT_LENGTH:
                    # 保留前N个字符，并添加截断标记
                    truncated_content = content[:MAX_TOOL_RESULT_LENGTH] + f"\n\n[数据已截断，原始长度: {len(content)} 字符，仅显示前 {MAX_TOOL_RESULT_LENGTH} 字符]"
                    # 创建新的ToolMessage，保留原始属性
                    truncated_msg = ToolMessage(
                        content=truncated_content,
                        tool_call_id=getattr(msg, 'tool_call_id', None),
                        name=getattr(msg, 'name', None)
                    )
                    truncated_messages.append(truncated_msg)
                    logger.warning(f"⚠️ [上下文管理] 工具返回数据过长 ({len(content)} 字符)，已截断至 {MAX_TOOL_RESULT_LENGTH} 字符")
                else:
                    truncated_messages.append(msg)
            else:
                truncated_messages.append(msg)
        
        messages = truncated_messages

        # 🔥 上下文管理：限制消息历史长度
        # 保留系统消息和最近的N条消息
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
        
        # 只保留最近的N条非系统消息
        if len(non_system_msgs) > MAX_MESSAGE_HISTORY:
            # 保留第一条（用户问题）和最后N-1条
            kept_messages = [non_system_msgs[0]] + non_system_msgs[-(MAX_MESSAGE_HISTORY-1):]
            logger.warning(f"⚠️ [上下文管理] 消息历史过长 ({len(non_system_msgs)} 条)，已截断至最近 {MAX_MESSAGE_HISTORY} 条")
            messages = system_msgs + kept_messages
        else:
            messages = system_msgs + non_system_msgs

        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            # 🔥 修复：检测文件模式，添加早期停止规则
            # 检查是否有文件数据源工具（inspect_file 或 analyze_dataframe）
            is_file_mode = any(
                getattr(tool, "name", "") in ["inspect_file", "analyze_dataframe"] 
                for tool in _cached_tools
            ) if _cached_tools else False
            
            # 如果是文件模式，添加强制早期停止规则（核弹级严格版本）
            if is_file_mode:
                file_mode_instructions = (
                    "\n\n## 🛑 [文件模式 - 核弹级强制停止] 🛑\n"
                    "【🚨 SYSTEM ALERT: FILE MODE ACTIVE】\n\n"
                    "你正在一个受限的执行环境中，步数限制非常低。\n\n"
                    "**目标（GOAL）**: 以最快的速度回答用户的具体问题。\n\n"
                    "**🚨 关键规则（CRITICAL RULES）**:\n\n"
                    "1. **一次性分析（ONE-SHOT ANALYSIS）**:\n"
                    "   - 尝试在 1-2 个复杂的 Pandas 查询中获取所有必要的数据。\n"
                    "   - 不要逐个查询表，如果可以将它们合并或一起检查。\n"
                    "   - 使用 groupby、agg、filter 等组合查询，而不是多次单独查询。\n\n"
                    "2. **立即回答（IMMEDIATE ANSWER）**:\n"
                    "   - 一旦你看到数字（例如：销量=567，销售额=1416933），你必须立即停止。\n"
                    "   - 不要尝试'验证'、'排名'或'分析分类'，除非用户明确要求。\n"
                    "   - 如果用户问'索尼卖得怎么样'，你找到了销量和销售额，立即报告这些数字，然后停止。\n"
                    "   - 不要为了'完善分析'而查询分类表或其他表。\n\n"
                    "3. **禁止行为（FORBIDDEN BEHAVIOR）**:\n"
                    "   - 如果用户只是问'索尼卖得怎么样'，不要创建'完整的分析报告'。\n"
                    "   - 只给出索尼的统计数据和一个快速对比，然后停止。\n"
                    "   - 不要试图获取'所有品牌排名'来对比，除非用户明确要求。\n"
                    "   - 不要重复查询相同的数据来'确认'。\n\n"
                    "4. **失败风险（FAILURE RISK）**:\n"
                    "   - 如果你超过 5 步，系统将崩溃，任务将失败。\n"
                    "   - 现在立即回答，不要等待！\n"
                    "   - 不要试图'完善'答案，立即停止并回答。\n\n"
                    "**工具（TOOLS）**:\n"
                    "- 使用 `analyze_dataframe` 获取数据。\n"
                    "- 只有在不知道列名时才使用 `inspect_file`。\n"
                    "- SQL 工具已被禁用。\n\n"
                    "**记住：看到数据 = 立即停止 = 立即回答。不要犹豫，不要完善，不要分析分类！**\n"
                )
                enhanced_system_prompt = system_prompt + file_mode_instructions
                messages = [SystemMessage(content=enhanced_system_prompt)] + messages
            else:
                messages = [SystemMessage(content=system_prompt)] + messages

        try:
            response = await llm_with_tools.ainvoke(messages)
        except OpenAIAuthenticationError as e:
            logger.warning(
                "LLM authentication failed for provider %s, trying fallback providers",
                preferred_provider,
                exc_info=True,
            )
            # 回退优先级：OpenRouter > 智谱AI
            fallback_provider = None
            if getattr(settings, "openrouter_api_key", None):
                fallback_provider = "openrouter"
                logger.info("尝试使用OpenRouter作为回退Provider")
            elif getattr(settings, "zhipuai_api_key", None):
                fallback_provider = "zhipu"
                logger.info("尝试使用智谱AI作为回退Provider")
            
            if fallback_provider:
                fallback_llm = create_llm(model=model, provider=fallback_provider)
                fallback_llm_with_tools = (
                    fallback_llm.bind_tools(_cached_tools) if _cached_tools else fallback_llm
                )
                response = await fallback_llm_with_tools.ainvoke(messages)
            else:
                raise Exception(f"所有LLM Provider都不可用。原始错误: {e}")
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


def verify_tool_calls(all_messages: List, data_source_type: str, database_url: str = None):
    """
    验证是否调用了必要工具
    
    Args:
        all_messages: 所有消息列表
        data_source_type: 数据源类型 ("file" 或 "sql")
        database_url: 数据库URL（用于自动检测数据源类型）
    
    Returns:
        (is_valid, error_message): 如果验证通过返回(True, None)，否则返回(False, 错误消息)
    """
    # 自动检测数据源类型（如果未提供）
    if not data_source_type and database_url:
        if (database_url.startswith("file://") or 
            database_url.startswith("/app/uploads/") or 
            database_url.startswith("/app/data/") or
            database_url.endswith((".xlsx", ".xls", ".csv")) or
            ".xlsx" in database_url or ".xls" in database_url or ".csv" in database_url):
            data_source_type = "file"
        else:
            data_source_type = "sql"
    
    # 提取所有工具调用
    tool_calls = []
    for msg in all_messages:
        if isinstance(msg, AIMessage):
            tool_calls_list = getattr(msg, 'tool_calls', None)
            if tool_calls_list:
                for tc in tool_calls_list:
                    if isinstance(tc, dict):
                        tool_name = tc.get("name", "").lower()
                    elif hasattr(tc, 'name'):
                        tool_name = str(tc.name).lower()
                    else:
                        tool_name = str(tc).lower()
                    tool_calls.append(tool_name)
    
    logger.info(f"🔍 [工具调用验证] 数据源类型: {data_source_type}, 检测到的工具调用: {tool_calls}")
    
    # 验证文件数据源
    if data_source_type == "file":
        required_tools = ["inspect_file", "analyze_dataframe"]
        # 检查是否调用了所有必需工具
        has_inspect_file = any("inspect_file" in tc or "get_column_info" in tc for tc in tool_calls)
        has_analyze_dataframe = any("analyze_dataframe" in tc or "python_interpreter" in tc for tc in tool_calls)
        
        if not has_inspect_file or not has_analyze_dataframe:
            missing_tools = []
            if not has_inspect_file:
                missing_tools.append("inspect_file")
            if not has_analyze_dataframe:
                missing_tools.append("analyze_dataframe")
            error_msg = f"文件数据源必须调用以下工具: {', '.join(missing_tools)}"
            logger.error(f"❌ [工具调用验证] {error_msg}")
            return False, error_msg
    
    # 验证SQL数据源
    elif data_source_type == "sql":
        required_tools = ["query", "execute_sql_safe"]
        # 检查是否调用了任一必需工具
        has_query = any("query" in tc or "execute_sql" in tc or "query_database" in tc for tc in tool_calls)
        
        if not has_query:
            error_msg = "SQL数据源必须调用query或execute_sql_safe工具"
            logger.error(f"❌ [工具调用验证] {error_msg}")
            return False, error_msg
    
    logger.info(f"✅ [工具调用验证] 验证通过，所有必需工具已调用")
    return True, None


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
    # 确保re模块在函数内部可访问（使用全局导入的re模块）
    # 注意：已经在文件顶部导入了re，这里使用别名避免作用域问题
    # 确保re模块在整个函数中可用（使用全局导入的re模块）
    # 注意：已经在文件顶部导入了re，这里直接使用re而不是re_module
    # 使用全局的re模块，避免作用域问题
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
        
        # 🔥 关键修复：如果是文件数据源，自动在查询中注入文件路径上下文
        # 这样AI就知道应该调用 inspect_file 和 analyze_dataframe 工具
        is_file_source = database_url and (
            database_url.startswith("file://") or 
            database_url.startswith("local://") or
            database_url.startswith("/app/data/") or
            database_url.endswith(".xlsx") or
            database_url.endswith(".xls") or
            database_url.endswith(".csv")
        )
        
        if is_file_source:
            import os
            # 提取文件名
            filename = os.path.basename(database_url)
            
            # 🔥🔥🔥 强化：更明确地告诉AI文件路径和调用方式
            # 增强用户查询，注入数据源上下文
            enhanced_question = f"""【🚨🚨🚨 强制要求 - 必须遵守 🚨🚨🚨】

当前数据源是文件类型，文件名：{filename}
文件路径：{database_url}

⚠️⚠️⚠️ 你必须按以下步骤执行（不可跳过任何一步）：⚠️⚠️⚠️

步骤1️⃣（必须执行）：
- 立即调用 inspect_file 工具
- 工具参数：file_path="{database_url}"
- 例如：inspect_file(file_path="{database_url}")
- 目的：查看文件结构和工作表列表（如果是Excel文件）

步骤2️⃣（必须执行）：
- 根据步骤1的结果，调用 analyze_dataframe 工具
- 工具参数：
  * file_path="{database_url}"
  * query="df.head()" 或 "df.to_string()" 或其他Pandas查询
  * sheet_name="工作表名称"（如果是Excel文件，使用步骤1返回的实际工作表名称）
- 目的：读取真实数据

步骤3️⃣（必须执行）：
- 基于步骤2返回的真实数据生成回答
- 绝对禁止使用示例数据（如Alice、Bob、Charlie等）
- 绝对禁止编造数据

❌ 如果你跳过步骤1或步骤2，直接生成答案，系统将自动拦截你的回答！

用户问题：{question}
"""
            logger.info(f"[数据源上下文注入] 检测到文件数据源，已增强查询以强制AI调用文件工具")
            logger.info(f"   原始问题: {question}")
            logger.info(f"   文件路径: {database_url}")
            question = enhanced_question

        # Collect all messages during execution
        all_messages = []
        final_content = ""
        executed_sql = None
        query_results = None
        chart_image = None  # Store chart image from MCP ECharts tool call
        
        # 🔥 幻觉检测相关变量（第三道防线）
        hallucination_detected = False
        hallucination_reason = []

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
                            # DEBUG: 打印所有消息类型
                            import sys
                            try:
                                print(f"[DEBUG] MESSAGE TYPE: {type(msg).__name__}", flush=True)
                            except UnicodeEncodeError:
                                logger.debug(f"MESSAGE TYPE: {type(msg).__name__}")
                            if isinstance(msg, AIMessage):
                                try:
                                    print(f"[DEBUG] AIMessage - has content: {bool(msg.content)}, content type: {type(msg.content)}, has tool_calls: {bool(getattr(msg, 'tool_calls', None))}", flush=True)
                                except UnicodeEncodeError:
                                    logger.debug(f"AIMessage - has content: {bool(msg.content)}, content type: {type(msg.content)}, has tool_calls: {bool(getattr(msg, 'tool_calls', None))}")
                                if msg.content:
                                    final_content = msg.content
                                    # DEBUG: 打印 LLM 原始输出
                                    try:
                                        print("=" * 80, flush=True)
                                        print("[DEBUG] FINAL LLM OUTPUT (Raw String):", flush=True)
                                        print("=" * 80, flush=True)
                                        print(final_content, flush=True)
                                        print("=" * 80, flush=True)
                                        sys.stdout.flush()
                                    except UnicodeEncodeError:
                                        logger.debug("FINAL LLM OUTPUT (Raw String)")
                                    logger.info(f"[DEBUG] FINAL LLM OUTPUT (length: {len(final_content)}): {final_content[:500]}...")
                                elif getattr(msg, 'tool_calls', None):
                                    try:
                                        print(f"[DEBUG] AIMessage has tool_calls but no content. Tool calls: {len(msg.tool_calls)}", flush=True)
                                    except UnicodeEncodeError:
                                        logger.debug(f"AIMessage has tool_calls but no content. Tool calls: {len(msg.tool_calls)}")
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

        # 确保final_content已初始化（如果异常导致未初始化）
        if 'final_content' not in locals() or final_content is None:
            final_content = ""
            logger.warning("⚠️ final_content未初始化，设置为空字符串")

        # Extract ECharts JSON configuration from LLM response
        # Look for [CHART_START]...{...}[CHART_END] pattern in final_content
        echarts_option_from_text = None
        # DEBUG: 在解析前再次打印最终内容
        try:
            print("=" * 80, flush=True)
            print("[DEBUG] FINAL CONTENT BEFORE PARSING:", flush=True)
            print("=" * 80, flush=True)
            print(final_content, flush=True)
            print("=" * 80, flush=True)
        except UnicodeEncodeError:
            logger.debug("FINAL CONTENT BEFORE PARSING")
        except Exception as e:
            logger.debug(f"打印final_content时出错: {e}")
        logger.info(f"[DEBUG] FINAL CONTENT BEFORE PARSING (length: {len(final_content) if final_content else 0}): {final_content[:500] if final_content else ''}...")
        
        cleaned_content = final_content if final_content else ""
        
        if final_content:
            chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
            match = re.search(chart_pattern, final_content)
            
            # DEBUG: 打印匹配结果
            if match:
                try:
                    print("=" * 80, flush=True)
                    print("[DEBUG] CHART PATTERN MATCHED!", flush=True)
                    print(f"[DEBUG] Matched JSON string (first 500 chars): {match.group(1)[:500]}", flush=True)
                    print("=" * 80, flush=True)
                except UnicodeEncodeError:
                    logger.debug("CHART PATTERN MATCHED!")
                    logger.debug(f"Matched JSON string (first 500 chars): {match.group(1)[:500]}")
                logger.info(f"[DEBUG] CHART PATTERN MATCHED! JSON string length: {len(match.group(1))}")
            else:
                try:
                    print("=" * 80, flush=True)
                    print("[DEBUG] CHART PATTERN NOT FOUND IN FINAL CONTENT!", flush=True)
                    print("=" * 80, flush=True)
                except UnicodeEncodeError:
                    logger.debug("CHART PATTERN NOT FOUND IN FINAL CONTENT!")
                logger.warning("[DEBUG] CHART PATTERN NOT FOUND IN FINAL CONTENT!")
            
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

        # 🔥🔥🔥 第四道防线：通用幻觉检测（适用于所有数据源类型，无论是否调用工具）
        # 即使调用了工具，也要检测回答中是否包含明显的幻觉测试数据
        logger.info(f"🔍 [通用幻觉检测] 开始检查 - final_content长度: {len(final_content) if final_content else 0}")
        
        # 🔧 改进：支持多种文件路径格式
        # 注意：re 模块已在文件顶部导入，不需要再次导入
        is_file_datasource = False
        has_inspect_file = False
        has_analyze_dataframe = False
        has_sql_query = False
        
        if database_url:
            # 检查是否是文件路径格式
            is_file_datasource = (
                database_url.startswith("file://") or  # MinIO路径格式
                database_url.startswith("/app/uploads/") or  # 容器内绝对路径
                database_url.startswith("/app/data/") or  # 容器内数据路径
                database_url.endswith((".xlsx", ".xls", ".csv")) or  # 直接以扩展名结尾
                ".xlsx" in database_url or ".xls" in database_url or ".csv" in database_url  # 路径中包含扩展名
            )
        
        # 检查工具调用情况（增强日志记录）
        logger.info(f"🔍 [工具调用检查] 开始检查工具调用，all_messages 数量: {len(all_messages)}")
        tool_calls_log = []  # 🔥 优先级5：记录所有工具调用的详细信息
        for msg in all_messages:
            if isinstance(msg, AIMessage):
                tool_calls = getattr(msg, 'tool_calls', None)
                if tool_calls:
                    for tc in tool_calls:
                        # 处理不同的 tool_calls 格式
                        if isinstance(tc, dict):
                            tool_name = tc.get("name", "").lower()
                            tool_args = tc.get("args", {})
                        elif hasattr(tc, 'name'):
                            tool_name = str(tc.name).lower()
                            tool_args = getattr(tc, 'args', {})
                        else:
                            tool_name = str(tc).lower()
                            tool_args = {}
                        
                        # 记录工具调用信息
                        tool_calls_log.append({
                            "tool": tool_name,
                            "args_preview": str(tool_args)[:200] if tool_args else "无参数",
                            "timestamp": "已记录"
                        })
                        
                        if "inspect_file" in tool_name or "get_column_info" in tool_name:
                            has_inspect_file = True
                        if "analyze_dataframe" in tool_name or "python_interpreter" in tool_name:
                            has_analyze_dataframe = True
                        if "query" in tool_name or "execute_sql" in tool_name or "query_database" in tool_name:
                            has_sql_query = True
            
            # 🔥 优先级5：记录工具返回结果
            elif isinstance(msg, ToolMessage):
                tool_name = getattr(msg, 'name', 'unknown')
                content = str(msg.content) if msg.content else ""
                content_preview = content[:200] if len(content) > 200 else content
                tool_calls_log.append({
                    "tool_result": tool_name,
                    "content_preview": content_preview,
                    "has_error": 'SYSTEM ERROR' in content or 'Error' in content or '错误' in content,
                    "timestamp": "已记录"
                })
        
        logger.info(f"🔍 [工具调用检查] 工具调用状态 - inspect_file: {has_inspect_file}, analyze_dataframe: {has_analyze_dataframe}, sql_query: {has_sql_query}")
        logger.info(f"📊 [工具调用日志] 共记录 {len(tool_calls_log)} 个工具调用/返回事件")
        for idx, log_entry in enumerate(tool_calls_log[:10]):  # 只记录前10个，避免日志过长
            logger.debug(f"   [{idx+1}] {log_entry}")
        
        # 🔥 优先级2：强制工具调用验证（在幻觉检测之前）
        # 如果AI没有调用必要工具，直接拦截并返回错误消息
        tool_calls_valid = True
        tool_verify_error = None
        
        # 只有在有回答内容时才进行验证（避免空回答时误拦截）
        if final_content and len(final_content.strip()) > 50:
            data_source_type_for_verify = "file" if is_file_datasource else "sql"
            tool_calls_valid, tool_verify_error = verify_tool_calls(all_messages, data_source_type_for_verify, database_url)
            
            if not tool_calls_valid:
                logger.error(f"🚫 [工具调用验证] 验证失败: {tool_verify_error}")
                hallucination_detected = True
                hallucination_reason = [tool_verify_error]
                
                # 强制返回友好的错误消息
                error_message = (
                    "⚠️ **工具调用验证失败**\n\n"
                    f"**错误原因：** {tool_verify_error}\n\n"
                    "**可能的原因：**\n"
                    "- AI未能正确调用必要的工具\n"
                    "- 工具调用失败或被跳过\n"
                    "- 数据源配置不正确\n\n"
                    "**建议操作：**\n"
                    "1. 请检查数据源是否正确配置\n"
                    "2. 确认数据源已成功加载（状态显示为✓）\n"
                    "3. 重新提问您的问题\n"
                )
                cleaned_content = error_message
                final_content = error_message
                query_results = None
                # 跳过后续的幻觉检测，因为已经拦截了
                logger.info(f"⏭️ [工具调用验证] 已拦截，跳过后续幻觉检测")
            else:
                logger.info(f"✅ [工具调用验证] 验证通过，继续执行幻觉检测")
        
        # 🔥 优先级4：检查工具返回的SYSTEM ERROR（在幻觉检测之前）
        # 如果任何工具返回了SYSTEM ERROR，强制拦截
        has_system_error = False
        system_error_details = []
        for msg in all_messages:
            if isinstance(msg, ToolMessage):
                content = str(msg.content) if msg.content else ""
                if 'SYSTEM ERROR' in content:
                    has_system_error = True
                    # 提取错误详情（前200字符）
                    error_preview = content[:200] if len(content) > 200 else content
                    system_error_details.append(error_preview)
                    logger.error(f"🚫 [SYSTEM ERROR检测] 工具返回了SYSTEM ERROR: {error_preview}")
        
        if has_system_error:
            logger.error(f"🚫 [SYSTEM ERROR检测] 检测到工具返回SYSTEM ERROR，强制拦截回答")
            hallucination_detected = True
            hallucination_reason = ["工具返回了SYSTEM ERROR，表示工具执行失败"]
            
            # 强制返回友好的错误消息
            error_message = (
                "⚠️ **数据获取失败**\n\n"
                "系统检测到工具执行失败，无法获取数据。\n\n"
                "**可能的原因：**\n"
                "- 数据源连接失败\n"
                "- 文件路径不正确或文件不存在\n"
                "- 数据库查询失败\n"
                "- 权限不足\n\n"
                "**建议操作：**\n"
                "1. 请检查数据源是否正确配置\n"
                "2. 确认数据源已成功加载（状态显示为✓）\n"
                "3. 检查文件路径是否正确\n"
                "4. 重新提问您的问题\n"
            )
            cleaned_content = error_message
            final_content = error_message
            query_results = None
            # 跳过后续的幻觉检测，因为已经拦截了
            logger.info(f"⏭️ [SYSTEM ERROR检测] 已拦截，跳过后续幻觉检测")
        else:
            logger.info(f"✅ [SYSTEM ERROR检测] 未检测到SYSTEM ERROR，继续执行幻觉检测")
        
        # 🔴 通用幻觉检测：无论数据源类型，都检测可疑数据
        # 🔥 关键修复：即使工具调用验证失败或检测到SYSTEM ERROR，也要执行幻觉检测
        # 因为AI可能在没有调用工具的情况下生成假数据，我们需要检测并拦截
        if final_content and len(final_content.strip()) > 50:
            # 1. 检测是否包含已知的幻觉测试数据（扩展列表）
            suspicious_keywords = [
                # 中文测试数据（扩展列表）
                "张三", "李四", "王五", "赵六", "钱七", "孙七", "周八", "吴九", "郑十",
                "张伟", "李娜", "王强", "刘芳", "陈明", "赵丽", "周杰", "吴敏", "孙强", "郑红",
                # 英文测试数据（扩展列表，包含所有常见测试名字）
                "John Doe", "Jane Smith", "Bob Johnson", "Alice", "Bob", "Charlie", 
                "David", "Eve", "Frank", "Grace", "Henry", "Irene", "Jack",
                "Diana",  # 🔥 新增：用户反馈的名字
                # 其他常见测试名字
                "Test User", "Sample User", "Demo User",
            ]
            # 🔥 关键修复：使用更严格的检测，确保能检测到所有假数据
            has_suspicious_data = any(keyword in final_content for keyword in suspicious_keywords)
            # 🔥 额外检查：如果包含多个可疑关键词，更可能是假数据
            suspicious_count = sum(1 for keyword in suspicious_keywords if keyword in final_content)
            if suspicious_count >= 2:  # 如果包含2个或更多可疑关键词，强制标记为可疑
                has_suspicious_data = True
                logger.warning(f"⚠️ 检测到多个可疑测试数据关键词（{suspicious_count}个），强制标记为可疑")
            
            # 🔥 优先级3：增强检测 - 特别检测"张三"、"李四"、"王五"、"赵六"连续出现的情况
            chinese_test_names = ["张三", "李四", "王五", "赵六"]
            chinese_test_name_pattern = r'(张三|李四|王五|赵六)'
            chinese_test_name_matches = re.findall(chinese_test_name_pattern, final_content)
            if len(chinese_test_name_matches) >= 2:  # 如果包含至少2个这些名字，很可能是假数据
                has_suspicious_data = True
                logger.warning(f"⚠️ 检测到连续的中文测试名字列表: {chinese_test_name_matches}")
            
            # 2. 检测连续的英文名字列表模式（🔥 新增：专门检测 "Alice, Bob, Charlie, Diana, Eve" 这样的模式）
            # 检测连续的英文名字（大写开头，3-20个字母）被逗号、顿号或换行分隔
            has_english_name_list = False
            # 🔥 改进：直接检测完整的"用户ID: X, 姓名/用户名: Alice"模式，并检查是否包含测试名字
            # 支持"姓名"和"用户名"两种格式
            user_id_name_pattern = r'用户ID:\s*\d+[,\s，]+(?:姓名|用户名):\s*([A-Z][a-z]+)'
            user_id_name_matches = re.findall(user_id_name_pattern, final_content, re.IGNORECASE)
            if user_id_name_matches:
                # 提取所有姓名
                common_test_names = ["alice", "bob", "charlie", "diana", "eve", "david", "frank", "grace", "henry", "irene", "jack"]
                test_name_count = sum(1 for name in user_id_name_matches if name.lower() in common_test_names)
                if test_name_count >= 2:  # 至少2个是测试名字
                    has_english_name_list = True
                    logger.warning(f"⚠️ 检测到连续的英文测试名字列表（用户ID格式）: {user_id_name_matches[:5]}")
            
            # 检测连续的英文名字列表（逗号分隔）
            if not has_english_name_list:
                english_name_pattern = r'\b([A-Z][a-z]{2,19}(?:,?\s*[A-Z][a-z]{2,19}){2,})'  # 至少3个连续的英文名字
                matches = re.findall(english_name_pattern, final_content)
                if matches:
                    for match in matches:
                        # 提取所有英文名字
                        names = re.findall(r'\b([A-Z][a-z]{2,19})\b', str(match))
                        if len(names) >= 3:
                            # 检查是否是常见的测试名字组合
                            common_test_names = ["alice", "bob", "charlie", "diana", "eve", "david", "frank", "grace", "henry", "irene", "jack"]
                            test_name_count = sum(1 for name in names if name.lower() in common_test_names)
                            if test_name_count >= 2:  # 至少2个是测试名字
                                has_english_name_list = True
                                logger.warning(f"⚠️ 检测到连续的英文测试名字列表: {names[:5]}")
                                break
            
            # 3. 检测具体的数据列表模式
            # 检测中文顿号分隔的列表: "张三、李四、王五"
            has_chinese_list = bool(re.search(r'[\u4e00-\u9fa5]{2,}、[\u4e00-\u9fa5]{2,}', final_content))
            # 🔥 优先级3：增强检测 - 特别检测包含"张三"、"李四"等测试名字的列表
            if not has_chinese_list:
                chinese_test_name_list_pattern = r'(张三|李四|王五|赵六)(、|，|,)(张三|李四|王五|赵六)'
                if re.search(chinese_test_name_list_pattern, final_content):
                    has_chinese_list = True
                    logger.warning(f"⚠️ 检测到包含测试名字的中文列表模式")
            # 检测数字+个模式: "5个用户", "10条记录"
            has_count_pattern = bool(re.search(r'[1-9]\d*\s*个', final_content))
            # 检测列表标记: "1. ", "- "
            has_list_markers = bool(re.search(r'(^|\n)\s*[-•*]\s+[\u4e00-\u9fa5]', final_content, re.MULTILINE))
            # 检测数字列表: "1. 张三\n2. 李四" 或 "用户ID: 1, 姓名: Alice"
            # 🔥 修复：添加对"用户1"、"用户2"等简单编号模式的检测
            has_numbered_list = bool(re.search(r'(^|\n)\s*\d+\.\s+[\u4e00-\u9fa5]', final_content, re.MULTILINE)) or \
                               bool(re.search(r'用户ID:\s*\d+', final_content)) or \
                               bool(re.search(r'用户[1-9]\d*', final_content)) or \
                               bool(re.search(r'用户编号:\s*\d+', final_content)) or \
                               bool(re.search(r'- 用户[1-9]\d*', final_content)) or \
                               bool(re.search(r'\* 用户[1-9]\d*', final_content))
            
            # 4. 检测规律的测试数据模式
            has_user_pattern = bool(re.search(r'user[0-9]+', final_content, re.IGNORECASE))
            has_test_pattern = bool(re.search(r'test[0-9]+', final_content, re.IGNORECASE))
            
            # 5. 检测是否是数据查询类问题的回答
            is_data_query = (
                ("用户" in final_content and "名称" in final_content) or 
                ("users" in final_content.lower() and "name" in final_content.lower()) or
                ("列名" in final_content or "工作表" in final_content) or
                ("列" in final_content and ("统计" in final_content or "查询" in final_content)) or
                ("所有" in final_content and ("用户" in final_content or "数据" in final_content)) or
                ("列出" in final_content) or
                ("显示" in final_content and "数据" in final_content)
            )
            
            # 6. 检查是否有工具返回的数据证据
            # 如果有工具调用但查询结果为空，说明可能没有真实数据
            has_tool_result_data = False
            for msg in all_messages:
                if isinstance(msg, ToolMessage):
                    content = msg.content
                    # 检查是否包含实际数据（非错误信息）
                    if isinstance(content, str) and content and \
                       'SYSTEM ERROR' not in content and \
                       'Error' not in content and \
                       '错误' not in content and \
                       '失败' not in content:
                        # 检查是否包含数据（至少有一些内容，不是空字符串）
                        if len(content.strip()) > 10:  # 至少有一些内容
                            has_tool_result_data = True
                            break
            
            # 7. 综合判断：如果回答中包含具体数据模式，且没有工具调用或没有工具返回数据，很可能是幻觉
            has_actual_data_pattern = (
                has_chinese_list or          # 包含中文列表
                has_numbered_list or         # 包含编号列表
                has_english_name_list or     # 🔥 新增：包含连续的英文名字列表
                (has_count_pattern and is_data_query)  # 包含数量且是数据查询
            )
            
            # 🔥 关键修复：对于文件数据源，如果没有调用工具，直接判定为幻觉
            should_block_file_datasource = is_file_datasource and not has_inspect_file and not has_analyze_dataframe
            
            # 🔥 关键修复：如果检测到明显的测试数据模式（如连续的英文测试名字），无论工具是否返回数据，都要拦截
            # 因为如果工具返回了真实数据，AI就不会生成"Alice, Bob, Charlie"这样的测试名字
            # 🔥 修复：添加对"用户1"、"用户2"等简单编号模式的检测（这是明显的假数据模式）
            has_simple_numbered_users = bool(re.search(r'用户[1-9]\d*', final_content)) and \
                                       bool(re.search(r'用户[1-9]\d*[、,，]\s*用户[1-9]\d*', final_content))  # 检测连续的"用户1、用户2"模式
            should_block_obvious_test_data = has_english_name_list or \
                                           (has_suspicious_data and has_numbered_list) or \
                                           has_simple_numbered_users  # 🔥 新增：检测到简单的编号用户模式
            
            # 🔥 关键修复：如果工具成功返回了数据，应该信任工具返回的数据
            # 只有当AI在没有调用工具或工具失败的情况下生成这些数据时，才应该拦截
            # 🔥 修复：如果工具成功调用并返回了数据，且工具调用验证通过，不应该拦截
            # 因为工具返回的数据可能是真实的（即使包含"张三"、"李四"等测试数据关键词）
            should_block_hallucination = False
            
            # 情况1：文件数据源未调用必要工具，直接拦截
            if should_block_file_datasource:
                should_block_hallucination = True
                logger.warning(f"⚠️ 文件数据源未调用必要工具，强制拦截")
            # 情况2：检测到明显的测试数据模式（如Alice、Bob、Charlie、Diana），无论是否有工具返回数据，都要拦截
            # 因为如果工具返回了真实数据，AI就不会生成这些测试名字
            elif should_block_obvious_test_data:
                should_block_hallucination = True
                logger.warning(f"⚠️ 检测到明显的测试数据模式（如Alice、Bob、Charlie、Diana），强制拦截（即使有工具返回数据）")
            # 情况3：工具成功返回了数据，且工具调用验证通过，不应该拦截（即使包含测试数据关键词）
            # 但前提是没有检测到明显的测试数据模式
            elif has_tool_result_data and tool_calls_valid:
                should_block_hallucination = False
                logger.info(f"✅ 工具成功返回了数据，且工具调用验证通过，不拦截（数据可能来自真实文件）")
            # 情况4：其他情况：检测到可疑数据，且没有工具返回数据，应该拦截
            elif (has_suspicious_data or has_actual_data_pattern) and not has_tool_result_data:
                should_block_hallucination = True
                logger.warning(f"⚠️ 检测到可疑数据模式，且没有工具返回数据，拦截")
            
            logger.info(f"🔍 [幻觉检测] 检测结果:")
            logger.info(f"   - 数据源类型: {'文件' if is_file_datasource else 'SQL数据库'}")
            logger.info(f"   - 包含可疑测试数据: {has_suspicious_data}")
            logger.info(f"   - 包含英文名字列表: {has_english_name_list}")
            logger.info(f"   - 包含中文列表: {has_chinese_list}")
            logger.info(f"   - 包含编号列表: {has_numbered_list}")
            logger.info(f"   - 包含简单编号用户模式: {has_simple_numbered_users}")
            logger.info(f"   - 包含数量模式: {has_count_pattern}")
            logger.info(f"   - 是数据查询: {is_data_query}")
            logger.info(f"   - 包含实际数据模式: {has_actual_data_pattern}")
            logger.info(f"   - 有工具返回数据: {has_tool_result_data}")
            logger.info(f"   - 文件数据源未调用工具: {should_block_file_datasource}")
            logger.info(f"   - 明显的测试数据模式: {should_block_obvious_test_data}")
            logger.info(f"   - 应该拦截: {should_block_hallucination}")
            logger.info(f"   - 工具调用日志: {len(tool_calls_log)} 个事件")
            
            # 🚨 关键修复：如果检测到明确的数据模式或可疑数据，强制拦截
            if should_block_hallucination:
                logger.error(f"🚫 [第四道防线] 检测到幻觉：AI生成了具体数据但可能未基于真实数据！")
                logger.error(f"   数据源类型: {'文件' if is_file_datasource else 'SQL'}")
                logger.error(f"   调用了工具: inspect_file={has_inspect_file}, analyze_dataframe={has_analyze_dataframe}, sql_query={has_sql_query}")
                logger.error(f"   有工具返回数据: {has_tool_result_data}")
                logger.error(f"   答案内容预览: {final_content[:500]}...")
                logger.error(f"   拦截原因: 可疑数据={has_suspicious_data}, 数据模式={has_actual_data_pattern}, 英文名字列表={has_english_name_list}")
                
                # 🔥 设置幻觉检测标志（用于前端显示）
                hallucination_detected = True
                hallucination_reason = []
                if has_suspicious_data:
                    hallucination_reason.append("检测到可疑的测试数据（如张三、李四、Alice、Bob、Charlie等）")
                if has_english_name_list:
                    hallucination_reason.append("检测到连续的英文测试名字列表（如Alice, Bob, Charlie, Diana, Eve）")
                if has_chinese_list:
                    hallucination_reason.append("检测到中文顿号分隔的列表模式")
                if has_numbered_list:
                    hallucination_reason.append("检测到编号列表模式（如用户ID: 1, 姓名: ...）")
                if has_simple_numbered_users:
                    hallucination_reason.append("检测到简单的编号用户模式（如用户1、用户2、用户3等）")
                if should_block_file_datasource:
                    hallucination_reason.append("文件数据源未调用必要的工具（inspect_file或analyze_dataframe）")
                
                # 强制返回友好的错误消息
                error_message = (
                    "⚠️ **数据安全拦截**\n\n"
                    "系统检测到AI可能生成了虚构的数据，为保证数据准确性已自动拦截。\n\n"
                    "**可能的原因：**\n"
                    "- 数据文件尚未正确上传或选择\n"
                    "- 文件路径不正确\n"
                    "- AI未能成功读取数据文件\n"
                    "- 工具调用失败或返回空数据\n\n"
                    "**建议操作：**\n"
                    "1. 请在左侧\"数据源管理\"中上传或选择正确的数据文件\n"
                    "2. 确认数据源已成功加载（状态显示为✓）\n"
                    "3. 重新提问您的问题\n\n"
                    f"**检测详情：** {', '.join(hallucination_reason) if hallucination_reason else '检测到可疑的数据模式'}"
                )
                cleaned_content = error_message
                final_content = error_message  # 🔥 确保两个变量都被设置
                query_results = None  # 清除可能存在的虚假数据
            else:
                logger.info(f"✓ [幻觉检测] 未检测到明确的幻觉模式，允许通过")


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

        # 🔥 优先级2：如果检测到幻觉，确保answer字段使用错误消息
        final_answer = cleaned_content or ""
        if hallucination_detected:
            # 构建错误消息
            error_message = (
                "⚠️ **数据验证失败**\n\n"
                "系统检测到AI助手可能返回了不准确的数据。\n\n"
            )
            if hallucination_reason:
                if isinstance(hallucination_reason, list):
                    error_message += f"**检测详情：** {', '.join(hallucination_reason)}\n\n"
                else:
                    error_message += f"**检测详情：** {hallucination_reason}\n\n"
            error_message += (
                "**可能的原因：**\n"
                "- AI未能正确调用数据查询工具\n"
                "- 工具返回的数据为空或错误\n"
                "- AI生成了测试数据而非真实数据\n\n"
                "**建议操作：**\n"
                "1. 请检查数据源是否正确配置\n"
                "2. 确认数据源已成功加载（状态显示为✓）\n"
                "3. 重新提问您的问题\n"
            )
            final_answer = error_message
            # 清除可能包含假数据的结果
            # 🔥 修复：不能将data设置为None，必须使用QueryResult()空实例
            query_result = QueryResult()  # 使用空QueryResult而不是None
            query_results = None
            logger.error(f"🚫 [Agent执行] 检测到幻觉，已更新answer字段为错误消息")
        
        # 🔥 构建metadata（包含幻觉检测信息）
        response_metadata = {
            "tool_error": tool_error_detected,
            "tool_status": "error" if tool_error_detected else "success",
            "tool_calls": tool_calls_info,
            "reasoning": None,  # 可以在这里添加推理过程
            # 🔥 添加幻觉检测元数据
            "hallucination_detected": hallucination_detected,
            "hallucination_reason": hallucination_reason if hallucination_detected else None,
        }
        
        response = VisualizationResponse(
            answer=final_answer,  # 🔥 使用处理后的answer（如果检测到幻觉，使用错误消息）
            sql=executed_sql or "",
            data=query_result,  # 现在query_result不会是None
            chart=chart_config,
            echarts_option=echarts_option,
            success=True,
            error=None,
            metadata=response_metadata,  # 🔥 添加metadata字段
        )

        # Return both dict (backward compatible) and response object
        # 🔥 修复：确保所有字段都有默认值，避免Pydantic验证错误
        # 🔥 修复：确保data字段始终是QueryResult实例，而不是字符串或其他类型
        if isinstance(query_results, QueryResult):
            data_field = query_results
        elif query_results is None:
            data_field = QueryResult()
        elif isinstance(query_results, (list, dict)):
            # 如果query_results是列表或字典，尝试转换为QueryResult
            try:
                data_field = QueryResult.from_raw_data(query_results if isinstance(query_results, list) else [query_results])
            except Exception as e:
                logger.warning(f"无法将query_results转换为QueryResult: {e}，使用空QueryResult")
                data_field = QueryResult()
        else:
            # 如果是字符串或其他类型，使用空QueryResult
            logger.warning(f"query_results是意外类型: {type(query_results)}，使用空QueryResult")
            data_field = QueryResult()
        
        return {
            "answer": cleaned_content or "",  # Use cleaned content, default to empty string
            "sql": executed_sql or "",  # 🔥 修复：确保sql字段始终是字符串
            "data": data_field,  # 🔥 修复：确保data字段始终是QueryResult实例
            "success": True,
            "error": None,
            "response": response,  # V5.1: structured response
            # 🔴 第三道防线：添加工具调用状态信息供前端使用（与response.metadata保持一致）
            "metadata": response_metadata
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        error_response = VisualizationResponse(
            success=False,
            error=str(e),
        )
        # 🔥 修复：确保异常情况下所有字段也有默认值
        return {
            "answer": "",  # 🔥 修复：使用空字符串而不是None
            "sql": "",  # 🔥 修复：使用空字符串而不是None
            "data": QueryResult(),  # 🔥 修复：使用空QueryResult而不是None
            "success": False,
            "error": str(e),
            "response": error_response,  # V5.1: structured response
            "metadata": {}  # 🔥 修复：添加空的metadata
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
