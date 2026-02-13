# -*- coding: utf-8 -*-
"""
Time Aggregation Middleware - 月度聚合修正中间件
=================================================

在工具调用前拦截并修正年度趋势查询的 SQL，
确保按月聚合而非按天聚合。

核心逻辑：
    - 检测年度趋势查询（如"2024年销售趋势"）
    - 修正 SQL 中的 GROUP BY 日期列为 GROUP BY DATE_TRUNC('month', ...)
    - 统一日志格式：[月度聚合修正] session=... changed=True ...

作者: BMad Master
版本: 1.2.0 (修复 DeepAgents 兼容性)
"""

import re
import logging
from typing import Any, Optional, Callable

# LangChain/LangGraph imports for deepagents compatibility
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command
from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)


class TimeAggregationMiddleware(AgentMiddleware):
    """
    时间聚合修正中间件 (DeepAgents 兼容)

    在工具调用前拦截 SQL 查询，自动修正年度趋势查询的
    时间聚合级别，确保返回月度数据而非日度数据。

    修正条件：
        1. 用户查询包含年度关键词（年、年度、202X）
        2. 用户查询包含趋势关键词（趋势、变化、走势、增长）
        3. SQL 包含 GROUP BY 日期列但没有月度聚合

    修正策略：
        - PostgreSQL: DATE_TRUNC('month', date_col)
        - MySQL: DATE_FORMAT(date_col, '%Y-%m')
        - SQLite: strftime('%Y-%m', date_col)
    """

    # 年度关键词
    YEAR_KEYWORDS = ["年", "年度", "今年", "去年", "前年", "year", "annual"]

    # 趋势关键词
    TREND_KEYWORDS = ["趋势", "变化", "走势", "增长", "下降", "按月", "每月", "月度", "trend"]

    # 明确要求细粒度的关键词（跳过修正）
    FINE_GRAIN_KEYWORDS = ["按天", "按日", "每天", "每日", "日度", "按周", "每周"]

    def __init__(
        self,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db_type: Optional[str] = None
    ):
        """
        初始化时间聚合修正中间件

        Args:
            session_id: 会话 ID
            tenant_id: 租户 ID
            db_type: 数据库类型 (postgres, mysql, sqlite 等)
        """
        self.session_id = session_id or "unknown"
        self.tenant_id = tenant_id or "default_tenant"
        self.db_type = db_type or "postgres"  # 默认 PostgreSQL
        self._fix_count = 0  # 修正计数

        # 缓存用户查询（从 state 中获取）
        self._user_query: str = ""

    def set_user_query(self, query: str) -> None:
        """设置当前用户查询（由外部设置）"""
        self._user_query = query or ""

    def _is_year_trend_query(self, user_query: str) -> bool:
        """检测是否为年度趋势查询"""
        if not user_query:
            return False

        query_lower = user_query.lower()

        # 检测年份（如 2024、2023-2025）
        has_year = bool(re.search(r"\b20\d{2}\b", query_lower))
        has_year_keyword = any(kw in query_lower for kw in self.YEAR_KEYWORDS)

        # 检测趋势关键词
        has_trend = any(kw in query_lower for kw in self.TREND_KEYWORDS)

        return (has_year or has_year_keyword) and has_trend

    def _has_explicit_fine_grain(self, user_query: str) -> bool:
        """检测用户是否明确要求细粒度数据"""
        if not user_query:
            return False
        return any(kw in user_query for kw in self.FINE_GRAIN_KEYWORDS)

    def _has_monthly_aggregation(self, sql: str) -> bool:
        """检测 SQL 是否已包含月度聚合"""
        sql_upper = sql.upper()
        monthly_patterns = [
            r"DATE_TRUNC\s*\(\s*'MONTH'",
            r"DATE_TRUNC\s*\(\s*\"MONTH\"",
            r"DATE_FORMAT\s*\(.*'%Y-%m'",
            r"TO_CHAR\s*\(.*'YYYY-MM'",
            r"STRFTIME\s*\(\s*'%Y-%m'",
            r"STRFTIME\s*\(\s*[^,]+,\s*'%Y-%m'",
        ]
        return any(re.search(pat, sql_upper, re.IGNORECASE) for pat in monthly_patterns)

    def _extract_group_by_date_col(self, sql: str) -> Optional[str]:
        """从 SQL 中提取 GROUP BY 的日期列名"""
        patterns = [
            r"GROUP BY\s+DATE_TRUNC\s*\(\s*'DAY'\s*,\s*([A-Za-z_][\w\.]*)\s*\)",
            r"GROUP BY\s+DATE_TRUNC\s*\(\s*\"DAY\"\s*,\s*([A-Za-z_][\w\.]*)\s*\)",
            r"GROUP BY\s+STRFTIME\s*\(\s*'%Y-%m-%d'\s*,\s*([A-Za-z_][\w\.]*)\s*\)",
            r"GROUP BY\s+DATE_FORMAT\s*\(\s*([A-Za-z_][\w\.]*)\s*,\s*'%Y-%m-%d'\s*\)",
            r"GROUP BY\s+TO_CHAR\s*\(\s*([A-Za-z_][\w\.]*)\s*,\s*'YYYY-MM-DD'\s*\)",
            r"GROUP BY\s+DATE\s*\(\s*([A-Za-z_][\w\.]*)\s*\)",
            r"GROUP BY\s+CAST\s*\(\s*([A-Za-z_][\w\.]*)\s+AS\s+DATE\s*\)",
            r"GROUP BY\s+([A-Za-z_][\w\.]*)\s*::\s*DATE",
            r"GROUP BY\s+([A-Za-z_][\w\.]*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _pick_month_expr(self, date_col: str) -> str:
        """根据数据库类型选择正确的月份表达式"""
        db_type_lower = self.db_type.lower()

        if db_type_lower in ["duckdb", "xlsx", "xls", "excel", "csv"]:
            return f"strftime(CAST({date_col} AS DATE), '%Y-%m')"
        if db_type_lower in ["sqlite", "sqlite3"]:
            return f"strftime('%Y-%m', {date_col})"
        if db_type_lower in ["mysql", "mariadb"]:
            return f"DATE_FORMAT({date_col}, '%Y-%m')"
        if db_type_lower in ["postgres", "postgresql"]:
            return f"DATE_TRUNC('month', {date_col})"

        # 回退：使用 PostgreSQL 语法
        return f"DATE_TRUNC('month', {date_col})"

    def _fix_sql_monthly(self, sql: str) -> str:
        """将 SQL 修正为月度聚合"""
        date_col = self._extract_group_by_date_col(sql)
        if not date_col:
            return sql  # 无法提取日期列，不修正

        # 检查是否需要修正（已聚合则跳过）
        if self._has_monthly_aggregation(sql):
            return sql

        # 选择正确的月份表达式
        month_expr = self._pick_month_expr(date_col)

        # 替换 SELECT 中的日期列
        date_col_pattern = re.escape(date_col)
        daily_expr_pattern = (
            rf"DATE_TRUNC\s*\(\s*'DAY'\s*,\s*{date_col_pattern}\s*\)|"
            rf"DATE_TRUNC\s*\(\s*\"DAY\"\s*,\s*{date_col_pattern}\s*\)|"
            rf"STRFTIME\s*\(\s*'%Y-%m-%d'\s*,\s*{date_col_pattern}\s*\)|"
            rf"DATE_FORMAT\s*\(\s*{date_col_pattern}\s*,\s*'%Y-%m-%d'\s*\)|"
            rf"TO_CHAR\s*\(\s*{date_col_pattern}\s*,\s*'YYYY-MM-DD'\s*\)"
        )
        select_pattern = rf"SELECT\s+((?:{daily_expr_pattern})|{date_col_pattern}(?:\s+as\s+\w+)?)(?=[,\s]|$)"

        corrected_sql = re.sub(
            select_pattern,
            f"{month_expr} as month",
            sql,
            flags=re.IGNORECASE
        )

        # 替换 GROUP BY 中的日期列
        group_by_pattern = (
            rf"GROUP BY\s+({date_col_pattern}\b|DATE\s*\(\s*{date_col_pattern}\s*\)|"
            rf"CAST\s*\(\s*{date_col_pattern}\s+AS\s+DATE\s*\)|"
            rf"{date_col_pattern}\s*::\s*DATE|{daily_expr_pattern})"
        )
        corrected_sql = re.sub(
            group_by_pattern,
            f"GROUP BY {month_expr}",
            corrected_sql,
            flags=re.IGNORECASE
        )

        # 替换 ORDER BY 中的日期列
        order_by_pattern = (
            rf"ORDER BY\s+({date_col_pattern}\b|DATE\s*\(\s*{date_col_pattern}\s*\)|"
            rf"CAST\s*\(\s*{date_col_pattern}\s+AS\s+DATE\s*\)|"
            rf"{date_col_pattern}\s*::\s*DATE|{daily_expr_pattern})"
        )
        corrected_sql = re.sub(
            order_by_pattern,
            f"ORDER BY {month_expr}",
            corrected_sql,
            flags=re.IGNORECASE
        )

        return corrected_sql

    def _extract_sql_from_tool_call(self, tool_call: dict) -> Optional[str]:
        """从工具调用中提取 SQL"""
        if not tool_call:
            return None

        args = tool_call.get("args", {})
        if isinstance(args, dict):
            return args.get("query") or args.get("sql", "")
        return None

    def _should_fix_tool(self, tool_name: str) -> bool:
        """判断工具是否需要修正"""
        return tool_name in ("execute_query", "execute_sql_safe", "query")

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以修正时间聚合 (同步版本）

        这是 deepagents 中间件接口的要求。

        Args:
            request: 工具调用请求
            handler: 处理函数

        Returns:
            ToolMessage 或 Command
        """
        # 获取工具调用
        tool_call = request.tool_call if isinstance(request.tool_call, dict) else {}

        tool_name = tool_call.get("name", "")

        # 只处理数据库查询工具
        if not self._should_fix_tool(tool_name):
            return handler(request)

        # 获取 SQL 参数
        sql = self._extract_sql_from_tool_call(tool_call)
        if not sql:
            return handler(request)

        # 使用缓存的用户查询或从 state 获取
        user_query = self._user_query
        if not user_query and hasattr(request, 'state'):
            # 尝试从 state 获取用户查询
            state = request.state or {}
            user_query = state.get("user_query") or state.get("question") or ""

        # 🔧 新增：从 contextvars 获取用户查询（最可靠的方式）
        if not user_query:
            try:
                from ..tools.database_tools import _get_user_query
                user_query = _get_user_query() or ""
            except (ImportError, AttributeError):
                pass

        # 检查是否需要修正
        if not self._is_year_trend_query(user_query):
            return handler(request)

        # 检查是否明确要求细粒度
        if self._has_explicit_fine_grain(user_query):
            return handler(request)

        # 检查是否已有月度聚合
        if self._has_monthly_aggregation(sql):
            return handler(request)

        # 执行修正
        fixed_sql = self._fix_sql_monthly(sql)
        if fixed_sql != sql:
            self._fix_count += 1
            logger.warning(
                f"[月度聚合修正] "
                f"session={self.session_id} "
                f"changed=True "
                f"reason='年度趋势查询缺少月度聚合' "
                f"fix_count={self._fix_count} "
                f"db_type={self.db_type} "
                f"sql_before={sql[:100] if len(sql) > 100 else sql}... "
                f"sql_after={fixed_sql[:100] if len(fixed_sql) > 100 else fixed_sql}..."
            )
            # 修改工具调用中的 SQL
            tool_call["args"] = dict(tool_call.get("args", {}))
            args = tool_call["args"]
            if "query" in args:
                args["query"] = fixed_sql
            if "sql" in args:
                args["sql"] = fixed_sql

            # 创建新的请求
            new_request = ToolCallRequest(
                tool_call=tool_call,
                tool=request.tool,
                state=request.state,
                runtime=request.runtime
            )
            return handler(new_request)

        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以修正时间聚合 (异步版本)

        这是 deepagents 中间件接口的要求。

        Args:
            request: 工具调用请求
            handler: 异步处理函数

        Returns:
            ToolMessage 或 Command
        """
        # 异步版本直接调用同步版本
        return self.wrap_tool_call(request, handler)


def create_time_aggregation_middleware(
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    db_type: Optional[str] = None
) -> TimeAggregationMiddleware:
    """
    创建时间聚合修正中间件的工厂函数

    Args:
        session_id: 会话 ID
        tenant_id: 租户 ID
        db_type: 数据库类型

    Returns:
        TimeAggregationMiddleware 实例
    """
    return TimeAggregationMiddleware(
        session_id=session_id,
        tenant_id=tenant_id,
        db_type=db_type
    )
