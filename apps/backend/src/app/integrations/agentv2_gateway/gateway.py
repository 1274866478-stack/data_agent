from __future__ import annotations

import asyncio
import importlib
import json
import logging
import threading
from contextvars import copy_context
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)


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
    return SimpleNamespace(
        is_valid=True,
        message="validation module unavailable",
        model_dump=lambda: {"is_valid": True},
    )


def _empty_list(*args, **kwargs):
    return []


def _load_optional_attrs(
    module_candidates: List[str],
    attr_names: List[str],
) -> Dict[str, Any]:
    loaded: Dict[str, Any] = {name: None for name in attr_names}
    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        for attr_name in attr_names:
            if loaded[attr_name] is None:
                loaded[attr_name] = getattr(module, attr_name, None)

        if all(loaded[attr_name] is not None for attr_name in attr_names):
            break
    return loaded


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
    VALIDATOR_MODULE_CANDIDATES = [
        "agent.tools.data_validator",
        "app.domains.query.agent.data_validator",
        "src.app.domains.query.agent.data_validator",
        "app.services.agent.data_validator",
        "src.app.services.agent.data_validator",
    ]
    VALIDATOR_ATTRS = [
        "build_cell_lineage",
        "generate_insights_from_rows",
        "recommend_chart",
        "smart_field_mapping",
        "validate_chart_fields_in_sql",
        "validate_sql_data_consistency",
    ]
    VALIDATOR_FALLBACKS: Dict[str, Callable[..., Any]] = {
        "validate_sql_data_consistency": _noop_validation,
        "smart_field_mapping": _noop_mapping,
        "recommend_chart": _noop_chart,
        "validate_chart_fields_in_sql": _noop_chart_validation,
        "build_cell_lineage": _empty_list,
        "generate_insights_from_rows": _empty_list,
    }
    SQL_TOOL_NAMES = {"execute_query", "query", "mcp_postgres_query"}

    def __init__(self) -> None:
        self._runtime = _RuntimeState()
        self._runtime_lock = threading.Lock()

    @staticmethod
    def _load_core_refs() -> Dict[str, Any]:
        from agent.core import AgentFactory, get_cache_stats, get_default_factory, get_response_cache
        from agent.graphs import run_swarm_query
        from agent.models import ChartConfig, QueryResult, VisualizationResponse
        from agent.tools import (
            clear_user_query_context,
            list_tables,
            set_user_query_context,
        )

        return {
            "AgentFactory": AgentFactory,
            "get_default_factory": get_default_factory,
            "get_response_cache": get_response_cache,
            "get_cache_stats": get_cache_stats,
            "run_swarm_query": run_swarm_query,
            "VisualizationResponse": VisualizationResponse,
            "QueryResult": QueryResult,
            "ChartConfig": ChartConfig,
            "list_tables": list_tables,
            "set_user_query_context": set_user_query_context,
            "clear_user_query_context": clear_user_query_context,
        }

    def _load_validator_refs(self) -> Dict[str, Any]:
        validator_attrs = _load_optional_attrs(
            self.VALIDATOR_MODULE_CANDIDATES,
            self.VALIDATOR_ATTRS,
        )
        missing_validator_attrs = [
            attr_name for attr_name, attr_value in validator_attrs.items() if attr_value is None
        ]
        if missing_validator_attrs:
            logger.debug(
                "[agentv2_gateway] validator attrs unavailable: %s",
                missing_validator_attrs,
            )
        return validator_attrs

    def _load_runtime(self) -> _RuntimeState:
        if self._runtime.loaded:
            return self._runtime

        with self._runtime_lock:
            if self._runtime.loaded:
                return self._runtime

            state = self._runtime
            state.loaded = True
            try:
                core_refs = self._load_core_refs()
                validator_refs = self._load_validator_refs()
                state.refs = {**core_refs, **validator_refs}
                state.available = True
                logger.debug("[agentv2_gateway] Agent runtime loaded")
            except Exception as exc:  # pragma: no cover - defensive path
                state.available = False
                state.error = exc
                logger.error("[agentv2_gateway] Failed to load Agent runtime: %s", exc)

        return state

    def is_available(self) -> bool:
        return self._load_runtime().available

    def _refs(self) -> Dict[str, Any]:
        return self._load_runtime().refs

    def get_runtime_error(self) -> Optional[Exception]:
        return self._load_runtime().error

    def get_default_factory(self):
        return self._refs()["get_default_factory"]()

    def get_agent_factory_class(self):
        return self._refs()["AgentFactory"]

    def get_response_cache(self):
        return self._refs()["get_response_cache"]()

    def get_cache_stats(self) -> Dict[str, Any]:
        return self._refs()["get_cache_stats"]()

    def _get_agent_factory_method(self, method_name: str) -> Optional[Callable[..., Any]]:
        agent_factory_cls = self.get_agent_factory_class()
        method = getattr(agent_factory_cls, method_name, None)
        return method if callable(method) else None

    def cache_table_names(
        self,
        *,
        tenant_id: str,
        table_names: List[str],
        connection_id: Optional[str],
    ) -> None:
        method = self._get_agent_factory_method("set_cached_table_names")
        if method is not None:
            method(
                tenant_id=tenant_id,
                table_names=table_names,
                connection_id=connection_id,
            )

    def get_cached_table_names(
        self,
        *,
        tenant_id: str,
        connection_id: Optional[str],
    ) -> Optional[List[str]]:
        method = self._get_agent_factory_method("get_cached_table_names")
        if method is None:
            return None
        try:
            return method(
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
        except Exception:
            logger.debug("[agentv2_gateway] failed to get cached table names", exc_info=True)
            return None

    async def list_tables(
        self,
        *,
        connection_id: Optional[str],
        db_session: Any,
        tenant_id: str,
    ) -> Any:
        list_tables_func = self._refs()["list_tables"]
        return await self._run_in_thread_with_context(
            list_tables_func,
            connection_id=connection_id,
            db_session=db_session,
            tenant_id=tenant_id,
        )

    @staticmethod
    async def _run_in_thread_with_context(func: Callable[..., Any], *args, **kwargs) -> Any:
        ctx = copy_context()
        return await asyncio.to_thread(ctx.run, func, *args, **kwargs)

    def _call_context_hook(self, hook_name: str, *args) -> bool:
        hook = self._refs().get(hook_name)
        if not hook:
            return False
        try:
            hook(*args)
            return True
        except Exception:
            logger.warning(
                "[agentv2_gateway] failed to call context hook: %s",
                hook_name,
                exc_info=True,
            )
            return False

    def set_user_query_context(self, query: str) -> bool:
        return self._call_context_hook("set_user_query_context", query)

    def clear_user_query_context(self) -> None:
        self._call_context_hook("clear_user_query_context")

    def get_data_validator_functions(self) -> Dict[str, Callable[..., Any]]:
        refs = self._refs()
        return {
            attr_name: refs.get(attr_name) or fallback
            for attr_name, fallback in self.VALIDATOR_FALLBACKS.items()
        }

    @staticmethod
    def _parse_tool_args(raw_args: Any, fallback: Any = None) -> Dict[str, Any]:
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        if isinstance(fallback, dict):
            return fallback
        return {}

    @staticmethod
    def _parse_dict_tool_call(tc: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        function_block = tc.get("function")
        if isinstance(function_block, dict):
            name = function_block.get("name") or tc.get("name")
            args = AgentV2Gateway._parse_tool_args(
                function_block.get("arguments"),
                tc.get("args"),
            )
            return name, args
        return tc.get("name"), AgentV2Gateway._parse_tool_args(tc.get("args"))

    @staticmethod
    def _parse_object_tool_call(tc: Any) -> Tuple[Optional[str], Dict[str, Any]]:
        return (
            getattr(tc, "name", None),
            AgentV2Gateway._parse_tool_args(getattr(tc, "args", {})),
        )

    @staticmethod
    def _iter_tool_calls(messages: List[Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls and isinstance(msg, dict):
                tool_calls = msg.get("tool_calls")
            if not tool_calls:
                continue

            for tc in tool_calls:
                if isinstance(tc, dict):
                    name, args = AgentV2Gateway._parse_dict_tool_call(tc)
                else:
                    name, args = AgentV2Gateway._parse_object_tool_call(tc)
                if name and isinstance(args, dict):
                    yield name, args

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
        for name, args in AgentV2Gateway._iter_tool_calls(messages):
            if name in AgentV2Gateway.SQL_TOOL_NAMES:
                sql = AgentV2Gateway._extract_sql_from_tool_args(args)
                if sql is not None:
                    return sql
        return ""

    @staticmethod
    def _extract_sql_from_tool_args(args: Dict[str, Any]) -> Optional[str]:
        sql = args.get("query") or args.get("sql") or args.get("q")
        if sql is None:
            return None
        return str(sql)

    @staticmethod
    def _rows_to_dicts(columns: List[Any], rows: List[Any]) -> List[Dict[str, Any]]:
        normalized_rows: List[Dict[str, Any]] = []
        if not isinstance(columns, list) or not isinstance(rows, list):
            return normalized_rows
        for row in rows:
            if isinstance(row, list):
                normalized_rows.append({col: val for col, val in zip(columns, row)})
        return normalized_rows

    @staticmethod
    def _extract_rows_payload(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list) and all(isinstance(row, dict) for row in payload):
            return payload
        if isinstance(payload, dict):
            return AgentV2Gateway._rows_to_dicts(
                payload.get("columns", []),
                payload.get("rows", []),
            )
        return []

    @staticmethod
    def _extract_data(messages: List[Any]) -> List[Dict[str, Any]]:
        for content in AgentV2Gateway._iter_tool_message_contents(messages):
            extracted = AgentV2Gateway._extract_rows_payload(content)
            if extracted:
                return extracted
        return []

    @staticmethod
    def _extract_data_from_result_payload(result: Any) -> List[Dict[str, Any]]:
        if not isinstance(result, dict):
            return []

        extracted = AgentV2Gateway._extract_rows_payload(result.get("data"))
        if extracted:
            return extracted
        return AgentV2Gateway._extract_rows_payload(result)

    @staticmethod
    def _is_tool_message(msg: Any) -> bool:
        if isinstance(msg, dict):
            return msg.get("role") == "tool"
        class_name = str(msg.__class__)
        return "ToolMessage" in class_name or "Tool" in class_name

    @staticmethod
    def _iter_tool_message_contents(messages: List[Any]) -> Iterator[Any]:
        for msg in messages:
            raw_content = None
            if AgentV2Gateway._is_tool_message(msg):
                raw_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if raw_content is None:
                continue

            try:
                content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                continue
            yield content

    @staticmethod
    def _extract_answer(result: Any, messages: List[Any]) -> str:
        answer = AgentV2Gateway._extract_answer_from_result(result)
        if answer:
            return answer
        return AgentV2Gateway._extract_answer_from_messages(messages)

    @staticmethod
    def _extract_answer_from_result(result: Any) -> str:
        if not isinstance(result, dict):
            return ""
        answer = AgentV2Gateway._nonempty_string(result.get("answer"))
        if answer is not None:
            return answer
        response_obj = result.get("response")
        response_answer = AgentV2Gateway._nonempty_string(getattr(response_obj, "answer", None))
        if response_answer is not None:
            return response_answer
        return ""

    @staticmethod
    def _extract_answer_from_messages(messages: List[Any]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content")
                content_text = AgentV2Gateway._nonempty_string(content)
                if role == "assistant" and content_text is not None:
                    return content_text
            else:
                content = getattr(msg, "content", None)
                class_name = msg.__class__.__name__.lower()
                content_text = AgentV2Gateway._nonempty_string(content)
                if content_text is not None and ("ai" in class_name or "assistant" in class_name):
                    return content_text
        return ""

    @staticmethod
    def _nonempty_string(value: Any) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            return value
        return None

    def parse_agent_result(self, result: Any) -> AgentInvocationResult:
        messages = self._extract_messages(result)
        sql = self._extract_sql(messages)
        data = self._extract_data(messages)
        answer = self._extract_answer(result, messages)
        success, error, sql, data = self._apply_result_overrides(
            result=result,
            sql=sql,
            data=data,
        )
        return AgentInvocationResult(
            success=success,
            answer=answer,
            sql=sql,
            data=data,
            messages=messages,
            error=error,
        )

    def _apply_result_overrides(
        self,
        *,
        result: Any,
        sql: str,
        data: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str], str, List[Dict[str, Any]]]:
        success = True
        error = None
        if not isinstance(result, dict):
            return success, error, sql, data

        if not sql:
            result_sql = result.get("sql")
            if isinstance(result_sql, str):
                sql = result_sql

        if not data:
            data = self._extract_data_from_result_payload(result)

        if isinstance(result.get("success"), bool):
            success = result["success"]
        error = result.get("error")
        if error:
            success = False
        return success, error, sql, data

    @staticmethod
    def _error_result(message: str) -> AgentInvocationResult:
        return AgentInvocationResult(
            success=False,
            answer="",
            sql="",
            data=[],
            error=message,
        )

    def _build_legacy_response_object(self, invoke_result: AgentInvocationResult) -> Any:
        runtime = self._load_runtime()
        if runtime.available:
            refs = self._refs()
            query_result_cls = refs["QueryResult"]
            chart_config_cls = refs["ChartConfig"]
            response_cls = refs["VisualizationResponse"]
            return response_cls(
                answer=invoke_result.answer or "",
                sql=invoke_result.sql or "",
                data=query_result_cls.from_raw_data(invoke_result.data),
                chart=chart_config_cls(),
                success=invoke_result.success,
                error=invoke_result.error,
            )

        return SimpleNamespace(
            answer=invoke_result.answer or "",
            sql=invoke_result.sql or "",
            data=SimpleNamespace(columns=[], rows=[], row_count=0),
            chart=SimpleNamespace(chart_type="table", title="", x_field=None, y_field=None),
            success=invoke_result.success,
            error=invoke_result.error,
        )

    @staticmethod
    def _runtime_unavailable_message(runtime: _RuntimeState) -> str:
        return str(runtime.error) if runtime.error else "AgentV2 runtime unavailable"

    @classmethod
    def _runtime_unavailable_swarm_result(cls, runtime: _RuntimeState) -> Dict[str, Any]:
        return {
            "error": cls._runtime_unavailable_message(runtime),
            "final_result": {},
        }

    @staticmethod
    def _build_user_message_payload(question: str) -> Dict[str, Any]:
        return {"messages": [{"role": "user", "content": question}]}

    async def _invoke_agent_with_timeout(
        self,
        *,
        agent: Any,
        question: str,
        timeout_seconds: float,
    ) -> Any:
        return await asyncio.wait_for(
            self._run_in_thread_with_context(
                agent.invoke,
                self._build_user_message_payload(question),
            ),
            timeout=timeout_seconds,
        )

    @staticmethod
    def _resolve_legacy_identity(
        *,
        thread_id: str,
        tenant_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> Tuple[str, str, str]:
        return (
            tenant_id or "default_tenant",
            user_id or "default_user",
            session_id or thread_id,
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
            return self._error_result(self._runtime_unavailable_message(runtime))

        try:
            agent = self._get_or_create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                connection_id=connection_id,
                db_session=db_session,
            )

            self.set_user_query_context(question)
            try:
                result = await self._invoke_agent_with_timeout(
                    agent=agent,
                    question=question,
                    timeout_seconds=timeout_seconds,
                )
            finally:
                self.clear_user_query_context()

            return self.parse_agent_result(result)
        except Exception as exc:
            logger.error("[agentv2_gateway] invoke_query failed: %s", exc, exc_info=True)
            return self._error_result(str(exc))

    def _get_or_create_agent(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: Optional[str],
        connection_id: Optional[str],
        db_session: Any,
    ) -> Any:
        factory = self._refs()["get_default_factory"]()
        return factory.get_or_create_agent(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id,
            db_session=db_session,
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
        _ = db_type  # legacy signature compatibility
        effective_tenant, effective_user, effective_session = self._resolve_legacy_identity(
            thread_id=thread_id,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )

        invoke_result = await self.invoke_query(
            question=question,
            tenant_id=effective_tenant,
            user_id=effective_user,
            session_id=effective_session,
            connection_id=connection_id,
            db_session=db_session,
        )

        response_obj = self._build_legacy_response_object(invoke_result)

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
            return self._runtime_unavailable_swarm_result(runtime)

        run_func = self._refs()["run_swarm_query"]
        return await run_func(
            query=query,
            tenant_id=tenant_id,
            llm=llm,
            cube_schema=cube_schema or {},
        )


agentv2_gateway = AgentV2Gateway()
