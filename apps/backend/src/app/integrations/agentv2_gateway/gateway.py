from __future__ import annotations

import asyncio
import json
import logging
from contextvars import copy_context
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentInvocationResult:
    success: bool
    answer: str = ""
    sql: str = ""
    data: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Any] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def row_count(self) -> int:
        return len(self.data)


@dataclass
class _RuntimeState:
    loaded: bool = False
    available: bool = False
    error: Optional[Exception] = None
    refs: Dict[str, Any] = field(default_factory=dict)


class AgentV2Gateway:
    """
    Single backend boundary for all AgentV2 calls.
    """

    def __init__(self) -> None:
        self._runtime = _RuntimeState()

    def _load_runtime(self) -> _RuntimeState:
        if self._runtime.loaded:
            return self._runtime

        state = self._runtime
        state.loaded = True
        try:
            from agent.core import AgentFactory, get_cache_stats, get_default_factory, get_response_cache
            import agent.middleware as middleware_module
            from agent.graphs.swarm_graph import run_swarm_query
            from agent.models import ChartConfig, QueryResult, VisualizationResponse
            from agent.tools.database_tools import _clear_user_query, _set_user_query, list_tables

            try:
                from agent.tools.data_validator import (  # type: ignore[attr-defined]
                    build_cell_lineage,
                    generate_insights_from_rows,
                    recommend_chart,
                    smart_field_mapping,
                    validate_chart_fields_in_sql,
                    validate_sql_data_consistency,
                )
            except Exception:
                build_cell_lineage = None
                generate_insights_from_rows = None
                recommend_chart = None
                smart_field_mapping = None
                validate_chart_fields_in_sql = None
                validate_sql_data_consistency = None

            state.refs = {
                "AgentFactory": AgentFactory,
                "get_default_factory": get_default_factory,
                "get_response_cache": get_response_cache,
                "get_cache_stats": get_cache_stats,
                "middleware_module": middleware_module,
                "run_swarm_query": run_swarm_query,
                "VisualizationResponse": VisualizationResponse,
                "QueryResult": QueryResult,
                "ChartConfig": ChartConfig,
                "list_tables": list_tables,
                "_set_user_query": _set_user_query,
                "_clear_user_query": _clear_user_query,
                "validate_sql_data_consistency": validate_sql_data_consistency,
                "smart_field_mapping": smart_field_mapping,
                "recommend_chart": recommend_chart,
                "validate_chart_fields_in_sql": validate_chart_fields_in_sql,
                "build_cell_lineage": build_cell_lineage,
                "generate_insights_from_rows": generate_insights_from_rows,
            }
            state.available = True
            logger.info("[agentv2_gateway] Agent runtime loaded")
        except Exception as exc:  # pragma: no cover - defensive path
            state.available = False
            state.error = exc
            logger.error("[agentv2_gateway] Failed to load Agent runtime: %s", exc)

        return state

    def is_available(self) -> bool:
        return self._load_runtime().available

    def get_runtime_error(self) -> Optional[Exception]:
        return self._load_runtime().error

    def get_default_factory(self):
        return self._load_runtime().refs["get_default_factory"]()

    def get_agent_factory_class(self):
        return self._load_runtime().refs["AgentFactory"]

    def get_response_cache(self):
        return self._load_runtime().refs["get_response_cache"]()

    def get_cache_stats(self) -> Dict[str, Any]:
        return self._load_runtime().refs["get_cache_stats"]()

    def get_middleware_module(self):
        return self._load_runtime().refs["middleware_module"]

    def cache_table_names(
        self,
        *,
        tenant_id: str,
        table_names: List[str],
        connection_id: Optional[str],
    ) -> None:
        agent_factory_cls = self.get_agent_factory_class()
        if hasattr(agent_factory_cls, "set_cached_table_names"):
            agent_factory_cls.set_cached_table_names(
                tenant_id=tenant_id,
                table_names=table_names,
                connection_id=connection_id,
            )

    async def list_tables(
        self,
        *,
        connection_id: Optional[str],
        db_session: Any,
        tenant_id: str,
    ) -> Any:
        list_tables_func = self._load_runtime().refs["list_tables"]
        return await asyncio.to_thread(
            list_tables_func,
            connection_id=connection_id,
            db_session=db_session,
            tenant_id=tenant_id,
        )

    def set_user_query_context(self, query: str) -> bool:
        set_func = self._load_runtime().refs.get("_set_user_query")
        if not set_func:
            return False
        try:
            set_func(query)
            return True
        except Exception:
            logger.warning("[agentv2_gateway] failed to set user query context", exc_info=True)
            return False

    def clear_user_query_context(self) -> None:
        clear_func = self._load_runtime().refs.get("_clear_user_query")
        if clear_func:
            try:
                clear_func()
            except Exception:
                logger.warning("[agentv2_gateway] failed to clear user query context", exc_info=True)

    def get_data_validator_functions(self) -> Dict[str, Callable[..., Any]]:
        refs = self._load_runtime().refs

        def _noop_validation(*args, **kwargs):
            return SimpleNamespace(
                is_valid=True,
                actual_columns=[],
                llm_fields=[],
                hallucinated_fields=[],
            )

        def _noop_mapping(*args, **kwargs):
            return SimpleNamespace(
                x_field=None,
                y_field=None,
                confidence=0.0,
                reasoning="validation module unavailable",
            )

        def _noop_chart(*args, **kwargs):
            return SimpleNamespace(
                chart_type="table",
                title="查询结果",
                reasoning="validation module unavailable",
            )

        def _noop_chart_validation(*args, **kwargs):
            return SimpleNamespace(is_valid=True, message="validation module unavailable", model_dump=lambda: {"is_valid": True})

        return {
            "validate_sql_data_consistency": refs.get("validate_sql_data_consistency") or _noop_validation,
            "smart_field_mapping": refs.get("smart_field_mapping") or _noop_mapping,
            "recommend_chart": refs.get("recommend_chart") or _noop_chart,
            "validate_chart_fields_in_sql": refs.get("validate_chart_fields_in_sql") or _noop_chart_validation,
            "build_cell_lineage": refs.get("build_cell_lineage") or (lambda *a, **k: []),
            "generate_insights_from_rows": refs.get("generate_insights_from_rows") or (lambda *a, **k: []),
        }

    @staticmethod
    def _extract_messages(result: Any) -> List[Any]:
        if isinstance(result, dict):
            messages = result.get("messages")
            if isinstance(messages, list):
                return messages
        if isinstance(result, list):
            return result
        if hasattr(result, "messages") and isinstance(result.messages, list):
            return result.messages
        return []

    @staticmethod
    def _extract_sql(messages: List[Any]) -> str:
        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls and isinstance(msg, dict):
                tool_calls = msg.get("tool_calls")
            if not tool_calls:
                continue

            for tc in tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name")
                    args = tc.get("args") or {}
                else:
                    name = getattr(tc, "name", None)
                    args = getattr(tc, "args", {}) or {}
                if name in {"execute_query", "query", "mcp_postgres_query"} and isinstance(args, dict):
                    sql = args.get("query") or args.get("sql") or args.get("q")
                    if sql:
                        return str(sql)
        return ""

    @staticmethod
    def _extract_data(messages: List[Any]) -> List[Dict[str, Any]]:
        for msg in messages:
            raw_content = None
            class_name = str(msg.__class__) if not isinstance(msg, dict) else msg.get("type", "")
            if "ToolMessage" in class_name or "Tool" in class_name or (isinstance(msg, dict) and msg.get("role") == "tool"):
                raw_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if raw_content is None:
                continue

            try:
                content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                continue

            if isinstance(content, dict) and "columns" in content and "rows" in content:
                columns = content.get("columns", [])
                rows = content.get("rows", [])
                if isinstance(columns, list) and isinstance(rows, list):
                    return [{col: val for col, val in zip(columns, row)} for row in rows if isinstance(row, list)]
            if isinstance(content, list) and all(isinstance(row, dict) for row in content):
                return content
        return []

    @staticmethod
    def _extract_answer(result: Any, messages: List[Any]) -> str:
        if isinstance(result, dict):
            answer = result.get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer

        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content")
                if role == "assistant" and isinstance(content, str):
                    return content
            else:
                content = getattr(msg, "content", None)
                class_name = msg.__class__.__name__.lower()
                if isinstance(content, str) and ("ai" in class_name or "assistant" in class_name):
                    return content
        return ""

    def parse_agent_result(self, result: Any) -> AgentInvocationResult:
        messages = self._extract_messages(result)
        sql = self._extract_sql(messages)
        data = self._extract_data(messages)
        answer = self._extract_answer(result, messages)
        return AgentInvocationResult(
            success=True,
            answer=answer,
            sql=sql,
            data=data,
            messages=messages,
        )

    async def invoke_query(
        self,
        *,
        question: str,
        tenant_id: str,
        user_id: str,
        session_id: Optional[str],
        connection_id: Optional[str],
        db_session: Any,
        timeout_seconds: float = 120.0,
    ) -> AgentInvocationResult:
        runtime = self._load_runtime()
        if not runtime.available:
            return AgentInvocationResult(
                success=False,
                answer="",
                sql="",
                data=[],
                error=str(runtime.error) if runtime.error else "AgentV2 runtime unavailable",
            )

        try:
            factory = runtime.refs["get_default_factory"]()
            agent = factory.get_or_create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                connection_id=connection_id,
                db_session=db_session,
            )

            self.set_user_query_context(question)
            try:
                ctx = copy_context()
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        ctx.run,
                        agent.invoke,
                        {"messages": [{"role": "user", "content": question}]},
                    ),
                    timeout=timeout_seconds,
                )
            finally:
                self.clear_user_query_context()

            return self.parse_agent_result(result)
        except Exception as exc:
            logger.error("[agentv2_gateway] invoke_query failed: %s", exc, exc_info=True)
            return AgentInvocationResult(
                success=False,
                answer="",
                sql="",
                data=[],
                error=str(exc),
            )

    async def run_legacy_query(
        self,
        *,
        question: str,
        thread_id: str,
        connection_id: Optional[str],
        tenant_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
        db_session: Any,
        db_type: str,
    ) -> Dict[str, Any]:
        effective_tenant = tenant_id or "default_tenant"
        effective_user = user_id or "default_user"
        effective_session = session_id or thread_id

        invoke_result = await self.invoke_query(
            question=question,
            tenant_id=effective_tenant,
            user_id=effective_user,
            session_id=effective_session,
            connection_id=connection_id,
            db_session=db_session,
        )

        runtime = self._load_runtime()
        if runtime.available:
            query_result_cls = runtime.refs["QueryResult"]
            chart_config_cls = runtime.refs["ChartConfig"]
            response_cls = runtime.refs["VisualizationResponse"]
            response_obj = response_cls(
                answer=invoke_result.answer or "",
                sql=invoke_result.sql or "",
                data=query_result_cls.from_raw_data(invoke_result.data),
                chart=chart_config_cls(),
                success=invoke_result.success,
                error=invoke_result.error,
            )
        else:
            response_obj = SimpleNamespace(
                answer=invoke_result.answer or "",
                sql=invoke_result.sql or "",
                data=SimpleNamespace(columns=[], rows=[], row_count=0),
                chart=SimpleNamespace(chart_type="table", title="", x_field=None, y_field=None),
                success=invoke_result.success,
                error=invoke_result.error,
            )

        return {
            "success": invoke_result.success,
            "answer": invoke_result.answer,
            "sql": invoke_result.sql,
            "data": invoke_result.data,
            "error": invoke_result.error,
            "response": response_obj,
            "messages": invoke_result.messages,
        }

    async def run_swarm_query(
        self,
        *,
        query: str,
        tenant_id: str,
        llm: Any = None,
        cube_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        runtime = self._load_runtime()
        if not runtime.available:
            return {
                "error": str(runtime.error) if runtime.error else "AgentV2 runtime unavailable",
                "final_result": {},
            }

        run_func = runtime.refs["run_swarm_query"]
        return await run_func(
            query=query,
            tenant_id=tenant_id,
            llm=llm,
            cube_schema=cube_schema or {},
        )


agentv2_gateway = AgentV2Gateway()
