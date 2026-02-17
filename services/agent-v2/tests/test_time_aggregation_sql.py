# -*- coding: utf-8 -*-
"""
时间聚合 SQL 修正器测试

覆盖重点：
1. 年度趋势查询按月聚合
2. 明确按天请求不修正
3. 不同数据库类型选择正确的月度表达式
"""

import os
import sys

# 添加父目录到路径以导入 sql_validator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sql_validator import SQLValidator


class TestTimeAggregationSQLFixer:
    """测试时间聚合 SQL 修正逻辑"""

    def test_fix_time_aggregation_duckdb(self):
        """DuckDB/Excel 年度趋势按月聚合"""
        sql = (
            "SELECT order_date, SUM(amount) as total "
            "FROM sales "
            "WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01' "
            "GROUP BY order_date "
            "ORDER BY order_date"
        )
        user_query = "2024年销售趋势"

        fixed_sql = SQLValidator.fix_time_aggregation_sql(sql, user_query, db_type="duckdb")

        assert "strftime(CAST(order_date AS DATE), '%Y-%m')" in fixed_sql
        assert "GROUP BY strftime(CAST(order_date AS DATE), '%Y-%m')" in fixed_sql
        assert "ORDER BY strftime(CAST(order_date AS DATE), '%Y-%m')" in fixed_sql

    def test_no_fix_when_daily_requested(self):
        """明确按天趋势不修正"""
        sql = (
            "SELECT order_date, SUM(amount) as total "
            "FROM sales "
            "WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01' "
            "GROUP BY order_date "
            "ORDER BY order_date"
        )
        user_query = "2024年销售趋势按天"

        fixed_sql = SQLValidator.fix_time_aggregation_sql(sql, user_query, db_type="duckdb")

        assert fixed_sql == sql

    def test_fix_time_aggregation_mysql(self):
        """MySQL 年度趋势按月聚合"""
        sql = (
            "SELECT order_date, SUM(amount) as total "
            "FROM sales "
            "WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01' "
            "GROUP BY order_date "
            "ORDER BY order_date"
        )
        user_query = "2024年销售趋势"

        fixed_sql = SQLValidator.fix_time_aggregation_sql(sql, user_query, db_type="mysql")

        assert "DATE_FORMAT(order_date, '%Y-%m')" in fixed_sql
        assert "GROUP BY DATE_FORMAT(order_date, '%Y-%m')" in fixed_sql

    def test_fix_time_aggregation_date_trunc_day(self):
        """Date trunc day should be corrected to month"""
        sql = (
            "SELECT DATE_TRUNC('day', order_date) as day, SUM(amount) as total "
            "FROM sales "
            "WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01' "
            "GROUP BY DATE_TRUNC('day', order_date) "
            "ORDER BY DATE_TRUNC('day', order_date)"
        )
        user_query = "2024 sales trend"

        fixed_sql = SQLValidator.fix_time_aggregation_sql(sql, user_query, db_type="duckdb")

        assert "strftime(CAST(order_date AS DATE), '%Y-%m')" in fixed_sql
        assert "DATE_TRUNC('day'" not in fixed_sql
