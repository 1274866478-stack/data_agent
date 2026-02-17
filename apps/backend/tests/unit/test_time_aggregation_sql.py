"""
Unit tests for validate_time_aggregation_sql.

测试场景:
    1. 年度趋势查询 → 月度聚合修正
    2. 按天查询 → 不修正
    3. 已有月度聚合 → 不修正
    4. DeepAgents 格式工具调用拦截
"""
import re

from backend.src.app.services.agent.tools import validate_time_aggregation_sql


def test_annual_trend_forces_monthly_grouping():
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="duckdb"
    )
    assert not is_valid
    assert "strftime" in corrected_sql
    assert re.search(r"GROUP BY\s+strftime", corrected_sql, re.IGNORECASE)
    assert re.search(r"SELECT\s+strftime", corrected_sql, re.IGNORECASE)


def test_daily_request_keeps_original_sql():
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="按天查看2024年销售趋势"
    )
    assert is_valid
    assert corrected_sql == sql


def test_annual_trend_date_trunc_day_forces_monthly():
    sql = (
        "SELECT DATE_TRUNC('day', order_date) AS day, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY DATE_TRUNC('day', order_date) "
        "ORDER BY DATE_TRUNC('day', order_date)"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="duckdb"
    )
    assert not is_valid
    assert "strftime" in corrected_sql
    assert "DATE_TRUNC('day'" not in corrected_sql


def test_annual_trend_keeps_monthly_sql():
    sql = (
        "SELECT strftime('%Y-%m', order_date) AS month, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY strftime('%Y-%m', order_date) "
        "ORDER BY strftime('%Y-%m', order_date)"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="sqlite"
    )
    assert is_valid
    assert corrected_sql == sql


def test_non_trend_query_not_modified():
    """非趋势查询不应被修正"""
    sql = (
        "SELECT category, COUNT(*) AS count "
        "FROM orders "
        "GROUP BY category"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="按类别统计订单数量",
        db_type="postgres"
    )
    assert is_valid
    assert corrected_sql == sql


def test_weekly_request_keeps_original():
    """明确要求周度数据不应被修正"""
    sql = (
        "SELECT DATE_TRUNC('week', order_date) AS week, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY DATE_TRUNC('week', order_date) "
        "ORDER BY DATE_TRUNC('week', order_date)"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="按周查看2024年销售",
        db_type="postgres"
    )
    assert is_valid
    assert corrected_sql == sql


def test_deepagents_tool_call_format():
    """测试 DeepAgents 格式工具调用的拦截"""
    # 模拟 DeepAgents 工具调用格式
    tool_calls = [
        {
            "name": "execute_query",
            "args": {
                "query": "SELECT order_date, SUM(total_amount) FROM orders GROUP BY order_date"
            },
            "id": "call_123"
        }
    ]

    # 模拟 apply_time_aggregation_fix_to_tool_calls_v2 函数
    from AgentV2.sql_agent import apply_time_aggregation_fix_to_tool_calls_v2

    question = "2024年销售趋势"
    fixed_calls = apply_time_aggregation_fix_to_tool_calls_v2(tool_calls, question)

    assert len(fixed_calls) == 1
    assert "strftime" in fixed_calls[0]["args"]["query"]
    assert "month" in fixed_calls[0]["args"]["query"]


def test_postgresql_month_expression():
    """测试 PostgreSQL 月度表达式"""
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="postgres"
    )
    assert not is_valid
    assert "DATE_TRUNC('month'" in corrected_sql


def test_mysql_month_expression():
    """测试 MySQL 月度表达式"""
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="mysql"
    )
    assert not is_valid
    assert "DATE_FORMAT" in corrected_sql
    assert "%Y-%m" in corrected_sql


def test_year_range_query():
    """测试年份范围查询"""
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01' "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="2024年销售趋势",
        db_type="postgres"
    )
    assert not is_valid
    assert "DATE_TRUNC('month'" in corrected_sql


def test_explicit_daily_request():
    """明确要求日度数据，不应修正"""
    sql = (
        "SELECT order_date, COUNT(*) AS daily_orders "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    is_valid, corrected_sql, _ = validate_time_aggregation_sql(
        sql,
        user_question="按天统计2024年每日订单数",
        db_type="postgres"
    )
    # 明确要求按天，不应修正
    assert is_valid
    # 但由于有"按天"关键词，应该保持原SQL
    assert corrected_sql == sql
