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
                        return await tool.ainvoke(tool_input, **kwargs)
                    except BaseException as e:
                        # Catch all exceptions including ExceptionGroup
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
                        logger.error(f"Tool async execution failed: {error_msg}", exc_info=True)
                        return f"Error executing tool: {error_msg}"
                if hasattr(tool, "invoke"):
                    try:
                        return await asyncio.to_thread(tool.invoke, tool_input, **kwargs)
                    except Exception as e:
                        logger.error(f"Tool thread execution failed: {e}", exc_info=True)
                        return f"Error executing tool: {str(e)}"
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
        )

    if provider == "openrouter":
        return ChatOpenAI(
            model=model or getattr(settings, "openrouter_default_model", "google/gemini-2.0-flash-exp"),
            api_key=api_key or getattr(settings, "openrouter_api_key", ""),
            base_url=base_url or getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1"),
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        )

    # default: deepseek
    return ChatOpenAI(
        model=model or getattr(settings, 'DEEPSEEK_MODEL', DEFAULT_MODEL),
        api_key=api_key or getattr(settings, 'DEEPSEEK_API_KEY', ''),
        base_url=base_url or getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
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
        config["echarts"] = {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 120.0,
        }

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
                return await t.ainvoke(tool_input, **kwargs)
            if hasattr(t, "invoke"):
                return await asyncio.to_thread(t.invoke, tool_input, **kwargs)
            raise RuntimeError("Tool has neither invoke nor ainvoke")

    return WrappedTool()


def create_secure_tools(mcp_tools: List[BaseTool]) -> List[BaseTool]:
    """
    Wrap MCP tools with security layer.

    The 'query' tool is replaced with our sanitized version.
    Other tools pass through with logging.

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
        else:
            # Pass through other tools (e.g., echarts)
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
            logger.warning(
                "Failed to load MCP tools; will retry without echarts if enabled",
                exc_info=True,
            )
            # If echarts was enabled, retry without it to keep SQL path working
            if enable_echarts and "echarts" in mcp_config:
                fallback_config = {k: v for k, v in mcp_config.items() if k != "echarts"}
                _cached_mcp_client = MultiServerMCPClient(fallback_config)
                raw_tools = await _cached_mcp_client.get_tools()
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
                            # Capture AI response
                            if isinstance(msg, AIMessage):
                                if msg.content:
                                    final_content = msg.content

                                # Extract SQL from tool calls
                                if msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        if tc.get("name") in ("query", "execute_sql_safe"):
                                            executed_sql = tc.get("args", {}).get("query") or tc.get("args", {}).get("sql")

                            # Capture tool results
                            elif isinstance(msg, ToolMessage):
                                try:
                                    content = msg.content
                                    if isinstance(content, str):
                                        query_results = json.loads(content)
                                    else:
                                        query_results = content
                                except (json.JSONDecodeError, TypeError):
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

        # Build VisualizationResponse
        query_result = QueryResult()
        chart_config = ChartConfig()
        echarts_option = None

        if query_results and isinstance(query_results, list):
            query_result = QueryResult.from_raw_data(query_results)

            # Auto-infer chart type and prepare config with ECharts option
            if executed_sql:
                _, chart_config, echarts_option = prepare_mcp_chart_request(
                    sql_result=query_results,
                    sql=executed_sql,
                    title="鏌ヨ缁撴灉"
                )

        response = VisualizationResponse(
            answer=final_content or "",
            sql=executed_sql or "",
            data=query_result,
            chart=chart_config,
            echarts_option=echarts_option,
            success=True,
            error=None,
        )

        # Return both dict (backward compatible) and response object
        return {
            "answer": final_content,
            "sql": executed_sql,
            "data": query_results,
            "success": True,
            "error": None,
            "response": response,  # V5.1: structured response
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
