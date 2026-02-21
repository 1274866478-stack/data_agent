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
import logging
import threading
from typing import Optional, List, Dict, Any, Callable

# 配置日志
logger = logging.getLogger(__name__)

# DeepAgents imports
from deepagents import create_deep_agent
# 不需要导入 FilesystemMiddleware，因为 create_deep_agent 已经自动添加了
# from deepagents.middleware import FilesystemMiddleware

# LangChain imports
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

# Local imports - V2 config
from ..agent_config_module import agent_config as v2_config
from .backend_runtime import import_first_available, run_async_sync
from .system_prompt import render_system_prompt_template

# Local imports - V2 modules
from ..middleware import (
    TenantIsolationMiddleware,
    SQLSecurityMiddleware,
    CHART_GUIDANCE_TEMPLATE,
    SemanticPriorityMiddleware,
    create_time_aggregation_middleware
)
from ..subagents import SubAgentManager, create_subagent_manager
from ..tools import get_database_tools, get_chart_tools
from ..tools.general_tools import get_general_tools
# 🟢 重新启用表推荐工具 - 已修复为返回实际表名
from ..tools.table_recommendation_tools import (
    get_recommended_tables_for_query,
    list_high_priority_tables
)
from ..tools.semantic_layer_tools import (
    resolve_business_term,
    get_semantic_measure,
    list_available_cubes,
    get_cube_measures,
    normalize_status_value
)

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
        - 多数据源支持 (Excel, PostgreSQL, MySQL)
    """

    # 类级别缓存
    _cached_agents: Dict[str, Any] = {}
    _cached_llms: Dict[tuple, BaseChatModel] = {}
    # 会话级表名缓存: {(tenant_id, connection_id): ["table1", "table2", ...]}
    _table_names_cache: Dict[tuple, List[str]] = {}
    _llm_cache_lock = threading.Lock()
    _agent_cache_lock = threading.Lock()
    _table_cache_lock = threading.Lock()

    DATA_SOURCE_SERVICE_MODULE_CANDIDATES = (
        "app.services.data_source_service",
        "app.domains.data_sources.service",
        "src.app.services.data_source_service",
        "src.app.domains.data_sources.service",
    )
    LOOP_DETECTION_CONFIG = {
        "max_tool_calls": 25,
        "loop_window_size": 8,
        "max_same_tool_calls": 5,
        "max_consecutive_failures": 4,
    }
    DEFAULT_TIME_AGGREGATION_DB_TYPE = "postgres"
    ENABLE_TABLE_CACHE_INJECTION = True
    LLM_MAX_TOKENS = 8000

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        enable_tenant_isolation: bool = True,
        enable_sql_security: bool = True,
        enable_subagents: bool = True,
        enable_chart_guidance: bool = True,
        enable_xai_logging: bool = True,  # 🔧 XAI 日志中间件开关
        enable_loop_detection: bool = True,  # 🔧 循环检测中间件开关
        enable_semantic_priority: bool = True,  # 🔧 语义层优先中间件开关 (已恢复，配合actual_table_name修复)
        enable_knowledge_tools: bool = False  # 🆕 知识检索工具开关
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
            enable_chart_guidance: 是否启用图表生成指南
            enable_xai_logging: 是否启用 XAI 日志中间件
            enable_loop_detection: 是否启用循环检测中间件
            enable_knowledge_tools: 是否启用知识检索工具（双知识系统）
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
        self.enable_chart_guidance = enable_chart_guidance
        self.enable_xai_logging = enable_xai_logging
        self.enable_loop_detection = enable_loop_detection  # 🔧 新增
        self.enable_semantic_priority = enable_semantic_priority  # 🔧 新增
        self.enable_knowledge_tools = enable_knowledge_tools  # 🆕 新增

        # SubAgent 管理器
        self._subagent_manager: Optional[SubAgentManager] = None

        # 连接上下文 (用于多数据源支持)
        self._connection_id: Optional[str] = None
        self._db_session: Optional[Any] = None
        self._data_source_service: Optional[Any] = None
        self._service_lock = threading.Lock()

    @property
    def subagent_manager(self) -> SubAgentManager:
        """获取或创建 SubAgent 管理器"""
        if self._subagent_manager is None:
            self._subagent_manager = create_subagent_manager(default_model=self.model)
        return self._subagent_manager

    def create_llm(self) -> BaseChatModel:
        """Create LLM instance with thread-safe cache."""
        llm_cache_key = (
            self.model.strip().lower(),
            float(self.temperature),
            int(self.max_tokens),
        )

        with self._llm_cache_lock:
            cached_llm = self._cached_llms.get(llm_cache_key)
            if cached_llm is not None:
                return cached_llm

            model_lower = self.model.lower()
            if "deepseek" in model_lower:
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
                cached_llm = self._create_chat_openai(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                    max_tokens=self.LLM_MAX_TOKENS,
                    extra_body={
                        "disable_strict_mode": True,
                        "ignore_error": True,
                    },
                )
            elif "zhipuai" in model_lower or "glm" in model_lower:
                api_key = os.environ.get("ZHIPUAI_API_KEY", "")
                base_url = os.environ.get("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
                cached_llm = self._create_chat_openai(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                    max_tokens=self.LLM_MAX_TOKENS,
                )
            else:
                cached_llm = self._create_chat_openai(
                    model=self.model,
                    temperature=self.temperature,
                )

            self._cached_llms[llm_cache_key] = cached_llm
            return cached_llm

    @staticmethod
    def _create_chat_openai(
        *,
        model: str,
        temperature: float,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> BaseChatModel:
        kwargs: Dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "streaming": True,
        }
        if api_key is not None:
            kwargs["api_key"] = api_key
        if base_url is not None:
            kwargs["base_url"] = base_url
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if extra_body is not None:
            kwargs["extra_body"] = extra_body
        return ChatOpenAI(**kwargs)

    def _load_connection_info(
        self,
        *,
        connection_id: Optional[str],
        tenant_id: Optional[str],
    ) -> Optional[Any]:
        """Load connection metadata from backend data source service."""
        if not connection_id or not self._db_session or not tenant_id:
            return None

        data_source_service = self._get_data_source_service()

        return run_async_sync(
            data_source_service.get_data_source_connection_info(
                connection_id=connection_id,
                tenant_id=tenant_id,
                db=self._db_session,
            ),
            timeout_seconds=10,
        )

    def _get_data_source_service(self) -> Any:
        if self._data_source_service is None:
            with self._service_lock:
                if self._data_source_service is None:
                    data_source_service_module = import_first_available(
                        self.DATA_SOURCE_SERVICE_MODULE_CANDIDATES,
                        required_attrs=("data_source_service",),
                    )
                    self._data_source_service = getattr(
                        data_source_service_module,
                        "data_source_service",
                    )
        return self._data_source_service

    def _load_tool_group(
        self,
        *,
        target: List[BaseTool],
        group_name: str,
        loader: Callable[[], List[BaseTool]],
        fail_fast: bool = True,
    ) -> None:
        """Load one tool group with uniform logging and error handling."""
        try:
            loaded_tools = loader() or []
            target.extend(loaded_tools)
            logger.debug(
                "[AgentFactory] added %s %s tools: %s",
                len(loaded_tools),
                group_name,
                self._tool_names(loaded_tools),
            )
        except (ImportError, AttributeError) as exc:
            logger.error("Failed to load %s tools (configuration error): %s", group_name, exc)
            if fail_fast:
                raise
        except Exception as exc:
            logger.warning("Unexpected error loading %s tools: %s", group_name, exc)

    @staticmethod
    def _tool_names(tools: List[Any]) -> List[str]:
        return [getattr(tool, "name", type(tool).__name__) for tool in tools]

    @staticmethod
    def _build_database_tools(
        *,
        connection_id: Optional[str],
        db_session: Optional[Any],
        tenant_id: Optional[str],
    ) -> List[BaseTool]:
        return get_database_tools(
            connection_id=connection_id,
            db_session=db_session,
            tenant_id=tenant_id,
        )

    @staticmethod
    def _build_chart_tools() -> List[BaseTool]:
        return get_chart_tools()

    @staticmethod
    def _build_general_tools() -> List[BaseTool]:
        return get_general_tools()

    @staticmethod
    def _build_semantic_tools() -> List[BaseTool]:
        from langchain_core.tools import StructuredTool

        return [
            StructuredTool.from_function(
                func=resolve_business_term,
                name="resolve_business_term",
                description=(
                    "解析业务术语，返回匹配的语义层定义。"
                    "使用场景：查询涉及业务指标（如'总收入'、'订单数'、'GMV'）时，"
                    "首先调用此工具获取标准定义和SQL表达式。"
                    "Args: term (str) - 业务术语，如'总收入'"
                )
            ),
            StructuredTool.from_function(
                func=get_semantic_measure,
                name="get_semantic_measure",
                description=(
                    "获取特定Cube中度量的完整定义（包括SQL表达式）。"
                    "Args: cube (str) - Cube名称, measure (str) - 度量名称"
                )
            ),
            StructuredTool.from_function(
                func=normalize_status_value,
                name="normalize_status_value",
                description=(
                    "规范化状态值（如'已完成' → 'completed'）。"
                    "Args: status (str) - 原始状态值"
                )
            ),
            StructuredTool.from_function(
                func=list_available_cubes,
                name="list_available_cubes",
                description=(
                    "列出所有可用的语义层Cube。"
                    "Args: None"
                )
            ),
            StructuredTool.from_function(
                func=get_cube_measures,
                name="get_cube_measures",
                description=(
                    "获取指定Cube的所有度量定义。"
                    "Args: cube (str) - Cube名称"
                )
            ),
        ]

    @staticmethod
    def _build_recommendation_tools() -> List[BaseTool]:
        from langchain_core.tools import StructuredTool

        return [
            StructuredTool.from_function(
                func=get_recommended_tables_for_query,
                name="get_recommended_tables",
                description=(
                    "🎯 智能表推荐工具 - 基于查询内容和实际表名推荐最相关的数据表\n\n"
                    "**使用场景**：当你需要查询数据但不确定使用哪个表时\n\n"
                    "**参数**：query (str) - 用户查询，如 '2023年销售趋势'\n\n"
                    "**返回**：推荐的表列表（使用实际表名）"
                )
            ),
            StructuredTool.from_function(
                func=list_high_priority_tables,
                name="list_high_priority_tables",
                description="列出所有高优先级的数据表"
            ),
        ]

    @staticmethod
    def _build_knowledge_tools(tenant_id: Optional[str]) -> List[BaseTool]:
        from ..knowledge.knowledge_tools import create_knowledge_tools

        return create_knowledge_tools(tenant_id=tenant_id or "default_tenant")


    @staticmethod
    def _resolve_tools(
        provided_tools: Optional[List[BaseTool]],
        *,
        fallback_builder: Callable[[], List[BaseTool]],
    ) -> List[BaseTool]:
        """Resolve tools with lazy fallback builder while preserving None-only behavior."""
        if provided_tools is not None:
            return provided_tools
        return fallback_builder()

    def _build_tools(
        self,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None,
        tenant_id: Optional[str] = None
    ) -> List[BaseTool]:
        """
        构建工具列表

        Args:
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）
            tenant_id: 租户 ID

        Returns:
            工具列表
        """
        tools: List[BaseTool] = []
        tool_load_plan: List[tuple[str, Callable[[], List[BaseTool]], bool]] = [
            (
                "database",
                lambda: self._build_database_tools(
                    connection_id=connection_id,
                    db_session=db_session,
                    tenant_id=tenant_id,
                ),
                True,
            ),
            ("chart", self._build_chart_tools, True),
            ("semantic", self._build_semantic_tools, True),
            ("general", self._build_general_tools, True),
        ]

        if self.enable_knowledge_tools:
            tool_load_plan.append(
                ("knowledge", lambda: self._build_knowledge_tools(tenant_id), False)
            )
        tool_load_plan.append(
            ("table recommendation", self._build_recommendation_tools, True)
        )

        for group_name, loader, fail_fast in tool_load_plan:
            self._load_tool_group(
                target=tools,
                group_name=group_name,
                loader=loader,
                fail_fast=fail_fast,
            )

        return tools

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
        _ = tools
        middleware: List[Any] = []

        if self.enable_tenant_isolation and tenant_id:
            middleware.append(
                TenantIsolationMiddleware(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                )
            )

        if self.enable_sql_security:
            middleware.append(SQLSecurityMiddleware())

        xai_middleware = self._create_xai_middleware(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
        self._append_if_not_none(middleware, xai_middleware)

        loop_middleware = self._create_loop_detection_middleware()
        self._append_if_not_none(middleware, loop_middleware)

        semantic_middleware = self._create_semantic_priority_middleware()
        self._append_if_not_none(middleware, semantic_middleware)

        time_aggregation_middleware = self._create_time_aggregation_middleware(
            tenant_id=tenant_id,
            session_id=session_id,
        )
        self._append_if_not_none(middleware, time_aggregation_middleware)

        return middleware

    @staticmethod
    def _append_if_not_none(target: List[Any], value: Optional[Any]) -> None:
        if value is not None:
            target.append(value)

    def _create_xai_middleware(
        self,
        *,
        tenant_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> Optional[Any]:
        if not (self.enable_xai_logging and session_id and tenant_id):
            return None

        from ..middleware import XAILoggerMiddleware

        return XAILoggerMiddleware(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            enable_detailed_logging=True,
            enable_persistence=True,
        )

    def _create_loop_detection_middleware(self) -> Optional[Any]:
        if not self.enable_loop_detection:
            return None

        from ..middleware import LoopDetectionMiddleware

        return LoopDetectionMiddleware(**self.LOOP_DETECTION_CONFIG)

    def _create_semantic_priority_middleware(self) -> Optional[Any]:
        if not self.enable_semantic_priority:
            return None

        return SemanticPriorityMiddleware(
            enable_detection=True,
            min_confidence=0.3,
            enable_logging=True,
        )

    @staticmethod
    def _create_time_aggregation_middleware(
        *,
        tenant_id: Optional[str],
        session_id: Optional[str],
    ) -> Optional[Any]:
        if not (session_id and tenant_id):
            return None
        return create_time_aggregation_middleware(
            session_id=session_id,
            tenant_id=tenant_id,
            db_type=AgentFactory.DEFAULT_TIME_AGGREGATION_DB_TYPE,
        )

    def _build_default_system_prompt(
        self,
        *,
        tools: Optional[List[BaseTool]],
        tenant_id: str,
        connection_id: Optional[str],
    ) -> str:
        tool_names = [t.name for t in tools] if tools else []
        base_system_prompt = self._build_system_prompt(
            tool_names=tool_names,
            connection_id=connection_id,
            tenant_id=tenant_id,
        )

        system_prompt = self.get_enhanced_prompt_with_cached_tables(
            base_system_prompt,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )

        if self.enable_chart_guidance:
            system_prompt = system_prompt + "\n\n" + CHART_GUIDANCE_TEMPLATE
            logger.debug(
                "[AgentFactory] chart guidance enabled; prompt markers chart_start=%s proportion_rule=%s case_when=%s len=%s",
                "[CHART_START]" in system_prompt,
                "占比类问题" in system_prompt,
                "CASE WHEN" in system_prompt,
                len(system_prompt),
            )
        else:
            logger.debug("[AgentFactory] chart guidance disabled")

        return system_prompt

    def _assign_request_context(
        self,
        *,
        connection_id: Optional[str],
        db_session: Optional[Any],
    ) -> None:
        self._connection_id = connection_id
        self._db_session = db_session

    def _resolve_system_prompt(
        self,
        *,
        system_prompt: Optional[str],
        tools: List[BaseTool],
        tenant_id: str,
        connection_id: Optional[str],
    ) -> str:
        if system_prompt is not None:
            return system_prompt
        return self._build_default_system_prompt(
            tools=tools,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )

    def create_agent(
        self,
        tenant_id: str = "default_tenant",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None
    ):
        """
        创建 Data Agent V2 实例

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表（如果为 None，使用默认工具集）
            system_prompt: 自定义系统提示
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）

        Returns:
            DeepAgents 实例
        """
        self._assign_request_context(connection_id=connection_id, db_session=db_session)

        llm = self.create_llm()
        resolved_tools = self._resolve_tools(
            tools,
            fallback_builder=lambda: self._build_tools(
                connection_id=connection_id,
                db_session=db_session,
                tenant_id=tenant_id,
            ),
        )

        middleware = self._build_middleware(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            tools=resolved_tools,
        )
        resolved_prompt = self._resolve_system_prompt(
            system_prompt=system_prompt,
            tools=resolved_tools,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )

        return create_deep_agent(
            model=llm,
            tools=resolved_tools or [],
            middleware=middleware,
            system_prompt=resolved_prompt,
        )

    def _resolve_data_source_prompt_context(
        self,
        *,
        connection_id: Optional[str],
        tenant_id: Optional[str],
    ) -> tuple[str, str]:
        """Resolve prompt context from current data source metadata."""
        is_excel = False
        sheets_info = ""

        if connection_id and tenant_id:
            try:
                connection_info = self._load_connection_info(
                    connection_id=connection_id,
                    tenant_id=tenant_id,
                )
                is_excel = bool(connection_info and connection_info.connection_type == "excel")
                if is_excel:
                    sheets_info = self._format_excel_sheets_info(connection_info)
            except Exception as exc:
                logger.warning("Failed to check data source type: %s", exc)

        data_source_type = "Excel File" if is_excel else "PostgreSQL Database"
        return data_source_type, sheets_info

    @staticmethod
    def _format_excel_sheets_info(connection_info: Any) -> str:
        sheet_names = ", ".join(connection_info.sheets) if connection_info.sheets else "Unknown"
        return f"\n**File**: {connection_info.file_path}\n**Available Sheets**: {sheet_names}"

    @staticmethod
    def _render_available_tools(tool_names: List[str]) -> str:
        if not tool_names:
            return "No tools available"
        return "\n".join(f"- {name}" for name in tool_names)

    def _build_system_prompt(
        self,
        tool_names: List[str],
        connection_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """
        构建系统提示词（根据数据源类型定制）

        Args:
            tool_names: 可用工具名称列表
            connection_id: 数据源连接 ID
            tenant_id: 租户 ID

        Returns:
            系统提示词
        """
        # 根据数据源类型构建提示词上下文
        data_source_type, sheets_info = self._resolve_data_source_prompt_context(
            connection_id=connection_id,
            tenant_id=tenant_id,
        )
        available_tools = self._render_available_tools(tool_names)

        return render_system_prompt_template(
            data_source_type=data_source_type,
            sheets_info=sheets_info,
            available_tools=available_tools,
        )

    # ========================================================================
    # 表名缓存管理
    # ========================================================================

    @classmethod
    def _make_table_cache_key(
        cls,
        tenant_id: str,
        connection_id: Optional[str],
    ) -> tuple[str, str]:
        return tenant_id, connection_id or "default"

    @staticmethod
    def _make_agent_cache_key(
        *,
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str],
        connection_id: Optional[str],
    ) -> str:
        return (
            f"{tenant_id}_"
            f"{user_id or 'none'}_"
            f"{session_id or 'none'}_"
            f"{connection_id or 'default'}"
        )

    @staticmethod
    def _render_cached_tables_context(cached_tables: List[str]) -> str:
        return f"""
## 📋 已缓存的表名列表 (Session Cache)

**注意**: 以下是上次查询时获取的表名列表。如果数据库结构发生变化，请重新调用 `list_tables()` 获取最新信息。

可用表: {', '.join(cached_tables)}

---
"""

    @classmethod
    def get_cached_table_names(
        cls,
        tenant_id: str,
        connection_id: Optional[str] = None
    ) -> Optional[List[str]]:
        """获取缓存的表名列表

        Args:
            tenant_id: 租户ID
            connection_id: 数据源连接ID

        Returns:
            缓存的表名列表，如果不存在则返回None
        """
        cache_key = cls._make_table_cache_key(tenant_id, connection_id)
        with cls._table_cache_lock:
            table_names = cls._table_names_cache.get(cache_key)
            return list(table_names) if table_names is not None else None

    @classmethod
    def set_cached_table_names(
        cls,
        tenant_id: str,
        table_names: List[str],
        connection_id: Optional[str] = None
    ) -> None:
        """设置缓存的表名列表

        Args:
            tenant_id: 租户ID
            table_names: 表名列表
            connection_id: 数据源连接ID
        """
        cache_key = cls._make_table_cache_key(tenant_id, connection_id)
        with cls._table_cache_lock:
            cls._table_names_cache[cache_key] = list(table_names)

    @staticmethod
    def _delete_mapping_keys(mapping: Dict[Any, Any], predicate: Callable[[Any], bool]) -> None:
        keys_to_remove = [key for key in mapping.keys() if predicate(key)]
        for key in keys_to_remove:
            del mapping[key]

    @classmethod
    def clear_table_cache(
        cls,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> None:
        """清除表名缓存

        Args:
            tenant_id: 租户ID，如果为None则清除所有租户的缓存
            connection_id: 数据源连接ID，如果为None则清除指定租户的所有缓存
        """
        with cls._table_cache_lock:
            if tenant_id is None:
                # 清除所有缓存
                cls._table_names_cache.clear()
            elif connection_id is None:
                # 清除指定租户的所有缓存
                cls._delete_mapping_keys(
                    cls._table_names_cache,
                    predicate=lambda key: key[0] == tenant_id,
                )
            else:
                # 清除指定租户和连接的缓存
                cache_key = cls._make_table_cache_key(tenant_id, connection_id)
                cls._table_names_cache.pop(cache_key, None)

    @classmethod
    def get_enhanced_prompt_with_cached_tables(
        cls,
        base_prompt: str,
        tenant_id: str,
        connection_id: Optional[str] = None
    ) -> str:
        """获取增强的提示词，包含缓存的表名信息

        Args:
            base_prompt: 基础提示词
            tenant_id: 租户ID
            connection_id: 数据源连接ID

        Returns:
            包含缓存表名信息的增强提示词

        Note:
            当前已禁用缓存注入功能，强制AI每次调用list_tables()。
            设置 ENABLE_TABLE_CACHE_INJECTION = True 可恢复缓存功能。
        """
        # 🔧 启用缓存注入，让LLM知道可用的表名
        # 这解决了LLM猜测表名（如inquiry_tenant_id、月度销售表）的问题
        if not cls.ENABLE_TABLE_CACHE_INJECTION:
            # 不注入缓存信息，强制AI调用list_tables()
            return base_prompt

        cached_tables = cls.get_cached_table_names(tenant_id, connection_id)
        if not cached_tables:
            return base_prompt

        cache_info = cls._render_cached_tables_context(cached_tables)
        return cache_info + base_prompt

    def _get_cached_agent(self, cache_key: str) -> Optional[Any]:
        with self._agent_cache_lock:
            return self._cached_agents.get(cache_key)

    def _cache_or_get_existing(
        self,
        *,
        cache_key: str,
        created_agent: Any,
        force_refresh: bool,
    ) -> Any:
        with self._agent_cache_lock:
            if not force_refresh:
                existing = self._cached_agents.get(cache_key)
                if existing is not None:
                    return existing
            self._cached_agents[cache_key] = created_agent
            return created_agent

    def get_or_create_agent(
        self,
        tenant_id: str = "default_tenant",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        force_refresh: bool = False,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None
    ):
        """
        获取或创建 Agent (单例模式)

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表
            force_refresh: 是否强制刷新
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）

        Returns:
            DeepAgents 实例
        """
        cache_key = self._make_agent_cache_key(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
        )

        if not force_refresh:
            cached_agent = self._get_cached_agent(cache_key)
            if cached_agent is not None:
                return cached_agent

        created_agent = self.create_agent(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            tools=tools,
            connection_id=connection_id,
            db_session=db_session
        )
        return self._cache_or_get_existing(
            cache_key=cache_key,
            created_agent=created_agent,
            force_refresh=force_refresh,
        )

    def reset_cache(self, tenant_id: Optional[str] = None):
        """重置 Agent 缓存"""
        with self._agent_cache_lock:
            if tenant_id is None:
                self._cached_agents.clear()
            else:
                self._delete_mapping_keys(
                    self._cached_agents,
                    predicate=lambda key: str(key).startswith(tenant_id),
                )

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
_default_factory_lock = threading.Lock()


def get_default_factory() -> AgentFactory:
    """获取默认的 AgentFactory 实例"""
    global _default_factory
    if _default_factory is None:
        with _default_factory_lock:
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
