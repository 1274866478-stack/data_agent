# -*- coding: utf-8 -*-
"""
SQL Tools Module

提供 SQL 安全验证、执行和 Schema 获取工具。
"""

import re
import logging
from typing import Optional, List, Any, Dict, Tuple

logger = logging.getLogger(__name__)


def ensure_monthly_aggregation(
    sql: str,
    user_question: str = ""
) -> Tuple[str, bool, str]:
    """
    最终兜底：将日级分组的年度/按月趋势 SQL 改写为月度聚合。

    Returns:
        (sql_after, changed, reason)
    """
    if not sql:
        return sql, False, "empty_sql"

    def _has_month(sql_text: str) -> bool:
        pats = [
            r"DATE_TRUNC\s*\(\s*'MONTH'",
            r"DATE_TRUNC\s*\(\s*\"MONTH\"",
            r"STRFTIME\s*\(\s*'%Y-%m'",
            r"TO_CHAR\s*\(.*YYYY-MM",
            r"DATE_FORMAT\s*\(.*%Y-%m",
        ]
        return any(re.search(p, sql_text, re.IGNORECASE) for p in pats)

    def _is_daily_group(sql_text: str) -> bool:
        return bool(
            re.search(r"GROUP\s+BY\s+order_date", sql_text, re.IGNORECASE)
            or re.search(r"DATE_TRUNC\s*\(\s*'DAY'\s*,\s*order_date", sql_text, re.IGNORECASE)
        )

    def _is_year_trend(question_or_sql: str) -> bool:
        q = question_or_sql or ""
        has_year = bool(re.search(r"\b20\d{2}\b", q))
        has_kw = any(k in q for k in ["趋势", "走势", "年度", "按月", "月度", "销售趋势", "同比", "环比"])
        return has_year or has_kw

    def _explicit_daily(q: str) -> bool:
        return any(k in q for k in ["按天", "每日", "每天", "日度", "逐日"])

    if _has_month(sql):
        return sql, False, "already_month"
    if not _is_daily_group(sql):
        return sql, False, "not_daily_group"
    combined = f"{user_question or ''} {sql}"
    if not _is_year_trend(combined):
        return sql, False, "not_trend"
    if _explicit_daily(combined):
        return sql, False, "explicit_daily"

    month_expr = "DATE_TRUNC('month', CAST(order_date AS DATE))"
    sql_new = re.sub(r"DATE_TRUNC\s*\(\s*'DAY'\s*,\s*order_date\s*\)", month_expr, sql, flags=re.IGNORECASE)
    sql_new = re.sub(r"\border_date\b", f"{month_expr} AS month", sql_new, count=1, flags=re.IGNORECASE)
    sql_new = re.sub(r"GROUP BY\s+order_date", f"GROUP BY {month_expr}", sql_new, flags=re.IGNORECASE)
    sql_new = re.sub(r"ORDER BY\s+order_date", f"ORDER BY {month_expr}", sql_new, flags=re.IGNORECASE)

    return sql_new, True, "fixed_to_month"


def validate_time_aggregation_sql(
    sql: str,
    user_question: str = "",
    db_type: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Validate SQL time aggregation query against user intent.
    Auto-correct SQL when query is for annual/monthly trends but lacks monthly aggregation.

    Args:
        sql: SQL query statement
        user_question: User original question
        db_type: Database type hint (postgresql/mysql/sqlite/duckdb/xlsx/csv)

    Returns:
        (is_valid, corrected_sql, error_message)
    """
    if not sql:
        return True, sql, ""

    def _split_top_level_csv(text: str) -> List[str]:
        parts = []
        buf = []
        depth = 0
        in_single = False
        in_double = False
        for ch in text:
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif not in_single and not in_double:
                if ch == "(":
                    depth += 1
                elif ch == ")" and depth > 0:
                    depth -= 1
            if ch == "," and depth == 0 and not in_single and not in_double:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf).strip())
        return parts

    def _has_explicit_fine_grain(q: str) -> bool:
        fine_keywords = ["按天", "每日", "每天", "按周", "每周", "7天", "周度", "日度"]
        return any(kw in q for kw in fine_keywords)

    def _is_annual_trend_query(q: str) -> bool:
        has_year = bool(re.search(r"\b20\d{2}\b", q)) or any(
            kw in q for kw in ["年", "年度", "今年", "去年", "前年"]
        )
        has_trend = any(
            kw in q for kw in ["趋势", "变化", "走势", "增长", "下降", "按月", "每月", "月度"]
        )
        return has_year and has_trend

    def _is_monthly_request(q: str) -> bool:
        monthly_keywords = [
            "按月", "每月", "每个月", "月度", "按月汇总",
            "按月统计", "按月分组", "按月查询", "按月趋势"
        ]
        return any(kw in q for kw in monthly_keywords)

    def _has_monthly_aggregation(sql_text: str) -> bool:
        sql_upper = sql_text.upper()
        monthly_patterns = [
            r"DATE_TRUNC\s*\(\s*'MONTH'",
            r"DATE_TRUNC\s*\(\s*\"MONTH\"",
            r"DATE_FORMAT\s*\(.*'%Y-%m'",
            r"TO_CHAR\s*\(.*'YYYY-MM'",
            r"STRFTIME\s*\(\s*'%Y-%m'",
            r"STRFTIME\s*\(\s*[^,]+,\s*'%Y-%m'",
            r"SUBSTRING\s*\(\s*[^,]+,\s*1\s*,\s*7\s*\)",
            r"SUBSTR\s*\(\s*[^,]+,\s*1\s*,\s*7\s*\)",
        ]
        return any(re.search(pat, sql_upper, re.IGNORECASE) for pat in monthly_patterns)

    def _pick_month_expr(sql_text: str, date_col: str, db_type_value: Optional[str]) -> str:
        db_type_lower = (db_type_value or "").lower()
        if db_type_lower in ["xlsx", "xls", "csv", "duckdb", "sqlite", "sqlite3"]:
            return f"strftime(CAST({date_col} AS DATE), '%Y-%m')"
        if db_type_lower == "mysql":
            return f"DATE_FORMAT({date_col}, '%Y-%m')"
        if db_type_lower in ["postgres", "postgresql"]:
            return f"DATE_TRUNC('month', {date_col})"
        sql_upper = sql_text.upper()
        if "STRFTIME" in sql_upper:
            return f"strftime({date_col}, '%Y-%m')"
        if "DATE_FORMAT" in sql_upper:
            return f"DATE_FORMAT({date_col}, '%Y-%m')"
        if "TO_CHAR" in sql_upper:
            return f"TO_CHAR({date_col}, 'YYYY-MM')"
        if "SUBSTR(" in sql_upper:
            return f"SUBSTR({date_col}, 1, 7)"
        if "SUBSTRING(" in sql_upper:
            return f"SUBSTRING({date_col}, 1, 7)"
        return f"DATE_TRUNC('month', {date_col})"

    def _extract_date_col(expr: str) -> str:
        tokens = re.findall(r"[A-Za-z_][\w\.]*", expr)
        return tokens[-1] if tokens else ""

    def _looks_like_date_col(name: str) -> bool:
        name_lower = name.lower()
        return any(
            kw in name_lower for kw in ["date", "time", "day", "month", "year", "created", "updated"]
        ) or any(
            kw in name for kw in ["日", "月", "年", "时间", "日期"]
        )

    def _replace_select_clause(sql_text: str, date_col: str, month_expr: str) -> str:
        match = re.search(r"select\s+(.*?)\s+from\s", sql_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return sql_text
        select_clause = match.group(1)
        columns = _split_top_level_csv(select_clause)
        new_columns = []
        replaced = False
        for col in columns:
            if re.search(rf"\b{re.escape(date_col)}\b", col, re.IGNORECASE):
                new_columns.append(f"{month_expr} as month")
                replaced = True
            else:
                new_columns.append(col.strip())
        if not replaced:
            new_columns.insert(0, f"{month_expr} as month")
        new_select = "SELECT " + ", ".join(new_columns) + " FROM "
        return sql_text[:match.start()] + new_select + sql_text[match.end():]

    def _replace_clause(
        sql_text: str,
        clause_name: str,
        date_col: str,
        month_expr: str
    ) -> Tuple[str, bool]:
        pattern = rf"({clause_name}\s+)(.*?)(\s+ORDER BY|\s+LIMIT|\s+OFFSET|\s+FETCH|\s*$)"
        match = re.search(pattern, sql_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return sql_text, False
        clause_body = match.group(2).strip()
        items = _split_top_level_csv(clause_body)
        replaced = False
        new_items = []
        for item in items:
            if re.search(rf"\b{re.escape(date_col)}\b", item, re.IGNORECASE):
                new_items.append(month_expr)
                replaced = True
            else:
                new_items.append(item.strip())
        if not replaced:
            return sql_text, False
        new_clause = match.group(1) + ", ".join(new_items) + match.group(3)
        return sql_text[:match.start()] + new_clause + sql_text[match.end():], True

    is_year_query = _is_annual_trend_query(user_question)
    is_month_query = _is_monthly_request(user_question)

    if (is_year_query or is_month_query) and _has_explicit_fine_grain(user_question):
        return True, sql, ""

    if not (is_year_query or is_month_query):
        return True, sql, ""  # Not year/month query

    if _has_monthly_aggregation(sql):
        return True, sql, ""  # Already has monthly aggregation

    group_by_match = re.search(
        r"GROUP BY\s+(.*?)(\s+ORDER BY|\s+LIMIT|\s+OFFSET|\s+FETCH|\s*$)",
        sql,
        re.IGNORECASE | re.DOTALL
    )

    if (is_year_query or is_month_query) and group_by_match:
        group_by_clause = group_by_match.group(1)
        group_by_items = _split_top_level_csv(group_by_clause)
        date_col = ""
        for item in group_by_items:
            candidate = _extract_date_col(item)
            if candidate and _looks_like_date_col(candidate):
                date_col = candidate
                break
        if not date_col and group_by_items:
            date_col = _extract_date_col(group_by_items[0])

        if date_col and any(agg in sql.upper() for agg in ["SUM(", "COUNT(", "AVG(", "MAX(", "MIN("]):
            corrected_sql = sql
            month_expr = _pick_month_expr(corrected_sql, date_col, db_type)
            corrected_sql = _replace_select_clause(corrected_sql, date_col, month_expr)
            corrected_sql, replaced_group_by = _replace_clause(
                corrected_sql, "GROUP BY", date_col, month_expr
            )
            corrected_sql, replaced_order_by = _replace_clause(
                corrected_sql, "ORDER BY", date_col, month_expr
            )

            if replaced_group_by and not replaced_order_by:
                corrected_sql = re.sub(
                    r"(\s+LIMIT|\s+OFFSET|\s+FETCH|\s*$)",
                    f" ORDER BY {month_expr}\\1",
                    corrected_sql,
                    flags=re.IGNORECASE
                )

            error_msg = (
                f"[时间聚合修正] 年度/月度趋势查询缺少月度聚合。\n"
                f"   当前SQL: GROUP BY {date_col}\n"
                f"   建议修改为: GROUP BY {month_expr}"
            )
            logger.warning(error_msg)
            return False, corrected_sql, error_msg

    return True, sql, ""


def sanitize_sql(sql: str) -> str:
    """
    清理 SQL 语句，移除注释和多余空白。

    Args:
        sql: 原始 SQL 语句

    Returns:
        清理后的 SQL 语句
    """
    if not sql:
        return ""

    # 移除 SQL 注释（-- 和 /* */）
    cleaned = re.sub(r'--.*?\n', '', sql)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)

    # 移除多余空白
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


def validate_sql_safety(sql: str) -> Tuple[bool, str]:
    """
    验证 SQL 是否只包含安全的 SELECT 操作。

    Args:
        sql: SQL 查询语句

    Returns:
        (is_safe, error_message)
    """
    if not sql:
        return False, "SQL 为空"

    sql_upper = sql.upper().strip()

    # 检查是否以 SELECT 或 WITH 开始（允许 CTE）
    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
        return False, "只允许 SELECT 查询"

    # 危险关键字检查
    dangerous_patterns = [
        r'\bDROP\s',
        r'\bDELETE\s',
        r'\bTRUNCATE\s',
        r'\bINSERT\s',
        r'\bUPDATE\s',
        r'\bALTER\s',
        r'\bCREATE\s',
        r'\bGRANT\s',
        r'\bREVOKE\s',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sql_upper):
            return False, f"检测到危险操作: {pattern}"

    return True, ""


def list_available_tables(db_conn) -> List[str]:
    """
    列出数据库中所有可用的表。

    Args:
        db_conn: 数据库连接对象

    Returns:
        表名列表
    """
    try:
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        result = db_conn.execute(query)
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return []


def get_table_schema(db_conn, table_name: str) -> Dict[str, Any]:
    """
    获取指定表的结构信息。

    Args:
        db_conn: 数据库连接对象
        table_name: 表名

    Returns:
        包含列信息的字典
    """
    try:
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        result = db_conn.execute(query, (table_name,))
        columns = []
        for row in result.fetchall():
            columns.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2],
                'default': row[3]
            })

        return {
            'table_name': table_name,
            'columns': columns
        }
    except Exception as e:
        logger.error(f"获取表 {table_name} 结构失败: {e}")
        return {}


def execute_sql_safe(
    db_conn,
    sql: str,
    params: Optional[List] = None,
    max_rows: int = 1000,
    user_question: str = ""
) -> Tuple[bool, Any, str]:
    """
    安全执行 SQL 查询，并在年度趋势场景下兜底改写为按月聚合。
    Args:
        db_conn: 数据库连接对象
        sql: SQL 查询语句
        params: 查询参数
        max_rows: 最大返回行数
        user_question: 原始用户问题（用于判定是否需要按月聚合）
    Returns:
        (success, result, error_message)
    """
    try:
        sql_fixed, changed, reason = ensure_monthly_aggregation(sql, user_question=user_question)
        if changed:
            logger.warning(f"⚠️ [月度修正-工具层] reason={reason} sql_len={len(sql)}")
        else:
            logger.debug(f"[月度修正-工具层] skipped reason={reason}")

        is_safe, error_msg = validate_sql_safety(sql_fixed)
        if not is_safe:
            return False, None, error_msg

        limited_sql = sql_fixed
        if max_rows > 0 and 'LIMIT' not in sql_fixed.upper():
            limited_sql = f"{sql_fixed.rstrip(';')} LIMIT {max_rows}"

        cursor = db_conn.execute(limited_sql, params or [])
        result = cursor.fetchmany(max_rows) if max_rows else cursor.fetchall()
        return True, result, ""

    except Exception as e:
        error_msg = f"SQL 执行错误: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def set_mcp_client(client):
    """
    设置 MCP 客户端实例。

    Args:
        client: MCP 客户端对象
    """
    global _mcp_client
    _mcp_client = client


# 全局 MCP 客户端
_mcp_client = None

