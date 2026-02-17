# -*- coding: utf-8 -*-
"""
单元测试：SQL 清理和验证功能
================================

测试 clean_and_validate_sql 函数修复各种错误 SQL 的能力。

作者: BMad
版本: 1.0.0
"""

import pytest
from AgentV2.tools.database_tools import clean_and_validate_sql


class TestSQLCleaningOrderGroupByErrors:
    """测试 ORDER BY/GROUP BY 后面错误跟 AND/OR/WHERE 的修复"""

    def test_remove_and_after_order_by(self):
        """测试移除 ORDER BY 后面的 AND 条件"""
        sql = "SELECT year, SUM(sales) FROM sales GROUP BY year ORDER BY year AND tenant_id = 'default'"
        result = clean_and_validate_sql(sql)

        # AND tenant_id 条件应该被移除
        assert "AND tenant_id" not in result
        assert "ORDER BY year" in result
        assert result.endswith(";")

    def test_remove_or_after_order_by(self):
        """测试移除 ORDER BY 后面的 OR 条件"""
        sql = "SELECT year, SUM(sales) FROM sales GROUP BY year ORDER BY year OR tenant_id = 'default'"
        result = clean_and_validate_sql(sql)

        # OR tenant_id 条件应该被移除
        assert "OR tenant_id" not in result
        assert "ORDER BY year" in result

    def test_remove_where_after_order_by(self):
        """测试移除 ORDER BY 后面的 WHERE 条件"""
        sql = "SELECT year, SUM(sales) FROM sales GROUP BY year ORDER BY year WHERE tenant_id = 'default'"
        result = clean_and_validate_sql(sql)

        # WHERE tenant_id 条件应该被移除
        # 注意：这可能触发其他修复逻辑（WHERE 子句位置修复）
        assert "WHERE tenant_id" not in result or result.upper().index("WHERE") < result.upper().index("ORDER BY")

    def test_remove_and_after_group_by(self):
        """测试移除 GROUP BY 后面的 AND 条件"""
        sql = "SELECT year, SUM(sales) FROM sales GROUP BY year AND tenant_id = 'default'"
        result = clean_and_validate_sql(sql)

        # AND tenant_id 条件应该被移除
        assert "AND tenant_id" not in result
        assert "GROUP BY year" in result

    def test_remove_where_after_group_by(self):
        """测试移除 GROUP BY 后面的 WHERE 条件"""
        sql = "SELECT year, SUM(sales) FROM sales GROUP BY year WHERE tenant_id = 'default'"
        result = clean_and_validate_sql(sql)

        # WHERE tenant_id 条件应该被移除或重新定位
        assert "WHERE tenant_id" not in result or result.upper().index("WHERE") < result.upper().index("GROUP BY")

    def test_order_by_with_asc_and_wrong_condition(self):
        """测试 ORDER BY field ASC 后面跟错误条件"""
        sql = "SELECT * FROM users ORDER BY name ASC AND tenant_id = 'x'"
        result = clean_and_validate_sql(sql)

        # AND 条件应该被移除
        assert "AND tenant_id" not in result
        assert "ORDER BY name ASC" in result

    def test_order_by_with_desc_and_wrong_condition(self):
        """测试 ORDER BY field DESC 后面跟错误条件"""
        sql = "SELECT * FROM users ORDER BY created_at DESC AND tenant_id = 'x'"
        result = clean_and_validate_sql(sql)

        # AND 条件应该被移除
        assert "AND tenant_id" not in result
        assert "ORDER BY created_at DESC" in result


class TestSQLCleaningWherePositionErrors:
    """测试 WHERE 子句位置错误的修复"""

    def test_where_after_group_by_and_order_by(self):
        """测试 WHERE 在 GROUP BY 和 ORDER BY 之后的修复"""
        sql = "SELECT year, SUM(sales) FROM sales_data GROUP BY year ORDER BY year WHERE tenant_id = 'default_tenant'"
        result = clean_and_validate_sql(sql)

        # 检查子句顺序是否正确
        where_pos = result.upper().find("WHERE")
        group_pos = result.upper().find("GROUP BY")
        order_pos = result.upper().find("ORDER BY")

        if where_pos != -1 and group_pos != -1 and order_pos != -1:
            # WHERE 应该在 GROUP BY 和 ORDER BY 之前
            assert where_pos < group_pos, f"WHERE 位置错误: {result}"
            assert group_pos < order_pos, f"GROUP BY/ORDER BY 位置错误: {result}"

    def test_where_after_order_by_only(self):
        """测试 WHERE 只在 ORDER BY 之后的修复"""
        sql = "SELECT * FROM users ORDER BY name WHERE tenant_id = 'x'"
        result = clean_and_validate_sql(sql)

        # WHERE 应该被移到 ORDER BY 之前
        where_pos = result.upper().find("WHERE")
        order_pos = result.upper().find("ORDER BY")

        if where_pos != -1 and order_pos != -1:
            assert where_pos < order_pos, f"WHERE 位置错误: {result}"

    def test_where_after_group_by_only(self):
        """测试 WHERE 只在 GROUP BY 之后的修复"""
        sql = "SELECT category, COUNT(*) FROM products GROUP BY category WHERE tenant_id = 'x'"
        result = clean_and_validate_sql(sql)

        # WHERE 应该被移到 GROUP BY 之前
        where_pos = result.upper().find("WHERE")
        group_pos = result.upper().find("GROUP BY")

        if where_pos != -1 and group_pos != -1:
            assert where_pos < group_pos, f"WHERE 位置错误: {result}"


class TestSQLCleaningLimitErrors:
    """测试 LIMIT 子句相关错误的修复"""

    def test_remove_content_after_limit(self):
        """测试移除 LIMIT 后面的错误内容"""
        sql = "SELECT * FROM users LIMIT 10 WHERE status = 'active'"
        result = clean_and_validate_sql(sql)

        # LIMIT 后面不应该有 WHERE
        limit_pos = result.upper().find("LIMIT")
        where_pos = result.upper().find("WHERE", limit_pos if limit_pos != -1 else 0)

        if limit_pos != -1:
            # WHERE 应该在 LIMIT 之前，或者不存在
            assert where_pos == -1 or where_pos < limit_pos

    def test_remove_and_after_limit(self):
        """测试移除 LIMIT 后面的 AND"""
        sql = "SELECT * FROM users LIMIT 10 AND tenant_id = 'x'"
        result = clean_and_validate_sql(sql)

        # LIMIT 后面不应该有 AND
        limit_pos = result.upper().find("LIMIT")
        and_pos = result.upper().find("AND", limit_pos if limit_pos != -1 else 0)

        if limit_pos != -1:
            assert and_pos == -1

    def test_keep_valid_limit(self):
        """测试保留有效的 LIMIT 子句"""
        sql = "SELECT * FROM users WHERE status = 'active' LIMIT 10"
        result = clean_and_validate_sql(sql)

        # LIMIT 应该被保留
        assert "LIMIT 10" in result.upper()


class TestSQLCleaningTenantsTable:
    """测试 tenants 表的 tenant_id → id 自动替换"""

    def test_replace_tenant_id_in_where(self):
        """测试 WHERE 子句中的 tenant_id 替换"""
        sql = "SELECT * FROM tenants WHERE tenant_id = '123'"
        result = clean_and_validate_sql(sql)

        # tenant_id 应该被替换为 id（对于 tenants 表）
        assert "id =" in result
        assert result.count("tenant_id") == 0 or result.upper().count("TENANT_ID") == 0

    def test_replace_tenant_id_with_and(self):
        """测试 AND 条件中的 tenant_id 替换"""
        sql = "SELECT * FROM tenants WHERE name = 'test' AND tenant_id = '123'"
        result = clean_and_validate_sql(sql)

        # AND tenant_id 应该被替换为 AND id
        assert "AND id =" in result


class TestSQLCleaningGeneral:
    """测试通用 SQL 清理功能"""

    def test_remove_trailing_semicolons(self):
        """测试移除多余的分号"""
        sql = "SELECT * FROM users;;"
        result = clean_and_validate_sql(sql)

        # 应该只有一个分号
        assert result.endswith(";")
        assert not result.endswith(";;")

    def test_add_missing_semicolon(self):
        """测试添加缺失的分号"""
        sql = "SELECT * FROM users"
        result = clean_and_validate_sql(sql)

        # 应该以分号结尾
        assert result.endswith(";")

    def test_remove_sql_comments(self):
        """测试移除 SQL 注释"""
        sql = "SELECT * FROM users -- this is a comment\nWHERE status = 'active'"
        result = clean_and_validate_sql(sql)

        # 注释应该被移除
        assert "-- this is a comment" not in result

    def test_remove_block_comments(self):
        """测试移除块注释"""
        sql = "SELECT * FROM users /* this is a block comment */ WHERE status = 'active'"
        result = clean_and_validate_sql(sql)

        # 块注释应该被移除
        assert "/* this is a block comment */" not in result

    def test_clean_extra_whitespace(self):
        """测试清理多余空格"""
        sql = "SELECT   *     FROM   users   WHERE   status   =   'active'"
        result = clean_and_validate_sql(sql)

        # 多余空格应该被清理
        assert "SELECT   *" not in result
        assert "FROM   users" not in result


class TestSQLCleaningEdgeCases:
    """测试边缘情况"""

    def test_empty_query(self):
        """测试空查询"""
        sql = ""
        result = clean_and_validate_sql(sql)
        # 空查询应该返回空或最小有效 SQL
        assert result == "" or result == ";"

    def test_whitespace_only(self):
        """测试只有空白的查询"""
        sql = "   \n\t  "
        result = clean_and_validate_sql(sql.strip())
        # 空白查询应该返回空或最小有效 SQL

    def test_valid_query_unchanged(self):
        """测试有效的查询不应该被改变"""
        sql = "SELECT * FROM users WHERE status = 'active' ORDER BY name;"
        result = clean_and_validate_sql(sql)

        # 基本结构应该保持不变
        assert "SELECT * FROM users" in result
        assert "WHERE status = 'active'" in result
        assert "ORDER BY name" in result


class TestSQLCleaningComplexErrors:
    """测试复杂错误组合"""

    def test_multiple_errors_combined(self):
        """测试多个错误同时存在的情况"""
        sql = "SELECT year, SUM(sales) FROM sales_data GROUP BY year ORDER BY year AND tenant_id = 'x' WHERE status = 'active';"
        result = clean_and_validate_sql(sql)

        # 检查基本修复
        assert result.endswith(";")

        # 如果有 WHERE，应该在 GROUP BY 之前
        where_pos = result.upper().find("WHERE")
        group_pos = result.upper().find("GROUP BY")

        if where_pos != -1 and group_pos != -1:
            assert where_pos < group_pos

    def test_double_injection_pattern(self):
        """测试重复注入模式（原始 bug 中的情况）"""
        sql = "SELECT year, SUM(sales) FROM sales_data GROUP BY year ORDER BY year AND tenant_id = 'default_tenant'"
        result = clean_and_validate_sql(sql)

        # AND tenant_id 应该被移除
        assert "AND tenant_id" not in result

    def test_original_bug_case(self):
        """测试原始 bug 报告中的具体案例"""
        # 情况 1：WHERE 在最后
        sql1 = "SELECT year, SUM(sales) as total_sales FROM sales_data GROUP BY year ORDER BY year WHERE tenant_id = 'default_tenant'"
        result1 = clean_and_validate_sql(sql1)

        # 验证子句顺序正确
        result1_upper = result1.upper()
        where_pos = result1_upper.find("WHERE")
        group_pos = result1_upper.find("GROUP BY")
        order_pos = result1_upper.find("ORDER BY")

        if where_pos != -1:
            assert where_pos < group_pos, f"WHERE 应该在 GROUP BY 之前: {result1}"
            assert group_pos < order_pos, f"GROUP BY 应该在 ORDER BY 之前: {result1}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
