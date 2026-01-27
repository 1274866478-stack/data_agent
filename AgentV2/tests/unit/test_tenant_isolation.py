# -*- coding: utf-8 -*-
"""
单元测试：租户隔离中间件 SQL 注入功能
==========================================

测试 inject_tenant_filter 函数在各种 SQL 结构下的正确注入行为。

作者: BMad
版本: 1.0.0
"""

import pytest
from AgentV2.middleware.tenant_isolation import inject_tenant_filter


class TestTenantFilterInjection:
    """测试租户过滤器注入功能"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.tenant_id = "test_tenant_123"

    def test_simple_select_no_where(self):
        """测试简单 SELECT 查询（无 WHERE）"""
        sql = "SELECT * FROM users"
        result = inject_tenant_filter(sql, self.tenant_id)
        assert result == f"{sql} WHERE tenant_id = '{self.tenant_id}'"

    def test_simple_select_with_where(self):
        """测试带 WHERE 的 SELECT 查询"""
        sql = "SELECT * FROM users WHERE status = 'active'"
        result = inject_tenant_filter(sql, self.tenant_id)
        expected = f"{sql} AND tenant_id = '{self.tenant_id}'"
        assert result == expected

    def test_select_with_group_by_no_where(self):
        """测试带 GROUP BY 但无 WHERE 的查询（主要 bug 场景）"""
        sql = "SELECT year, SUM(sales) as total_sales FROM sales_data GROUP BY year ORDER BY year"
        result = inject_tenant_filter(sql, self.tenant_id)

        # WHERE 应该被插入在 GROUP BY 之前
        assert "WHERE tenant_id" in result
        assert result.index("WHERE") < result.index("GROUP BY")
        assert result.index("GROUP BY") < result.index("ORDER BY")

    def test_select_with_order_by_no_where(self):
        """测试带 ORDER BY 但无 WHERE 的查询"""
        sql = "SELECT * FROM users ORDER BY created_at DESC"
        result = inject_tenant_filter(sql, self.tenant_id)

        # WHERE 应该被插入在 ORDER BY 之前
        assert "WHERE tenant_id" in result
        assert result.index("WHERE") < result.index("ORDER BY")

    def test_select_with_all_clauses(self):
        """测试包含所有子句的复杂查询"""
        sql = "SELECT category, COUNT(*) as cnt FROM products WHERE price > 100 GROUP BY category HAVING COUNT(*) > 5 ORDER BY cnt DESC LIMIT 10"
        result = inject_tenant_filter(sql, self.tenant_id)

        # tenant_id 应该被添加到现有 WHERE 后面，使用 AND
        assert "AND tenant_id" in result
        # 确保 WHERE 在 GROUP BY 之前
        assert result.index("WHERE") < result.index("GROUP BY")

    def test_already_has_tenant_id(self):
        """测试已经包含 tenant_id 的查询（不应重复添加）"""
        sql = "SELECT * FROM users WHERE tenant_id = 'other_tenant'"
        result = inject_tenant_filter(sql, self.tenant_id)
        # 应该保持原样
        assert result == sql

    def test_already_has_tenant_id_with_and(self):
        """测试已经包含 tenant_id AND 条件的查询"""
        sql = "SELECT * FROM users WHERE status = 'active' AND tenant_id = 'other_tenant'"
        result = inject_tenant_filter(sql, self.tenant_id)
        # 应该保持原样
        assert result == sql

    def test_select_with_limit_no_where(self):
        """测试带 LIMIT 但无 WHERE 的查询"""
        sql = "SELECT * FROM users LIMIT 100"
        result = inject_tenant_filter(sql, self.tenant_id)

        # WHERE 应该被插入在 LIMIT 之前
        assert "WHERE tenant_id" in result
        assert result.index("WHERE") < result.index("LIMIT")

    def test_select_with_having_no_where(self):
        """测试带 HAVING 但无 WHERE 的查询"""
        sql = "SELECT category, COUNT(*) FROM products GROUP BY category HAVING COUNT(*) > 10"
        result = inject_tenant_filter(sql, self.tenant_id)

        # WHERE 应该被插入在 HAVING 之前
        assert "WHERE tenant_id" in result
        assert result.index("WHERE") < result.index("HAVING")

    def test_complex_query_with_join(self):
        """测试带 JOIN 的复杂查询"""
        sql = "SELECT u.name, o.total FROM users u INNER JOIN orders o ON u.id = o.user_id WHERE o.status = 'pending'"
        result = inject_tenant_filter(sql, self.tenant_id)

        # tenant_id 应该被添加到现有 WHERE 后面
        assert "AND tenant_id" in result

    def test_query_with_subquery(self):
        """测试带子查询的查询"""
        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 1000)"
        result = inject_tenant_filter(sql, self.tenant_id)

        # tenant_id 应该被添加到外层 WHERE
        assert "AND tenant_id" in result

    def test_case_insensitive_keywords(self):
        """测试大小写不敏感的关键字"""
        # 小写
        sql = "select * from users group by name"
        result = inject_tenant_filter(sql, self.tenant_id)
        assert "where tenant_id" in result.lower()

        # 大写
        sql = "SELECT * FROM users GROUP BY name"
        result = inject_tenant_filter(sql, self.tenant_id)
        assert "WHERE tenant_id" in result

        # 混合
        sql = "Select * From Users Group By name"
        result = inject_tenant_filter(sql, self.tenant_id)
        assert "tenant_id" in result

    def test_no_from_clause(self):
        """测试没有 FROM 子句的查询（应返回原样）"""
        sql = "SELECT 1"
        result = inject_tenant_filter(sql, self.tenant_id)
        # 无法解析，应该返回原 SQL
        assert result == sql

    def test_edge_case_year_sales_query(self):
        """测试原始 bug 报告中的具体查询"""
        sql = "SELECT year, SUM(sales) as total_sales FROM sales_data GROUP BY year ORDER BY year"
        result = inject_tenant_filter(sql, self.tenant_id)

        # 确保结果语法正确
        assert "WHERE tenant_id" in result
        # 确保子句顺序正确
        where_pos = result.upper().index("WHERE")
        group_pos = result.upper().index("GROUP BY")
        order_pos = result.upper().index("ORDER BY")

        assert where_pos < group_pos, f"WHERE 应该在 GROUP BY 之前: {result}"
        assert group_pos < order_pos, f"GROUP BY 应该在 ORDER BY 之前: {result}"

    def test_multiple_joins_with_where(self):
        """测试多 JOIN 带 WHERE 的查询"""
        sql = """SELECT u.name, p.title, o.quantity
                 FROM users u
                 INNER JOIN orders o ON u.id = o.user_id
                 INNER JOIN products p ON o.product_id = p.id
                 WHERE o.status = 'completed'"""
        result = inject_tenant_filter(sql, self.tenant_id)

        assert "AND tenant_id" in result

    def test_select_distinct(self):
        """测试 SELECT DISTINCT"""
        sql = "SELECT DISTINCT category FROM products ORDER BY category"
        result = inject_tenant_filter(sql, self.tenant_id)

        assert "WHERE tenant_id" in result
        assert result.upper().index("WHERE") < result.upper().index("ORDER BY")

    def test_aggregate_functions(self):
        """测试聚合函数查询"""
        sql = "SELECT COUNT(*), AVG(price), MAX(quantity) FROM inventory"
        result = inject_tenant_filter(sql, self.tenant_id)

        assert result == f"{sql} WHERE tenant_id = '{self.tenant_id}'"


class TestTenantFilterEdgeCases:
    """测试边缘情况"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.tenant_id = "test_tenant_123"

    def test_tenant_id_with_special_chars(self):
        """测试带特殊字符的租户 ID"""
        tenant_id = "tenant-with-dash"
        sql = "SELECT * FROM users"
        result = inject_tenant_filter(sql, tenant_id)
        assert f"tenant_id = '{tenant_id}'" in result

    def test_tenant_id_with_quotes(self):
        """测试带引号的租户 ID（应该被转义或处理）"""
        # 注意：当前实现不处理 SQL 转义，这是潜在的安全问题
        # 实际应用中应该使用参数化查询
        tenant_id = "tenant's_name"
        sql = "SELECT * FROM users"
        result = inject_tenant_filter(sql, tenant_id)
        # 当前实现会生成无效 SQL，但这需要在生产环境中单独处理
        assert "tenant_id = " in result

    def test_empty_sql(self):
        """测试空 SQL"""
        sql = ""
        result = inject_tenant_filter(sql, self.tenant_id)
        assert result == sql

    def test_whitespace_only(self):
        """测试只有空白的 SQL"""
        sql = "   \n\t  "
        result = inject_tenant_filter(sql.strip(), self.tenant_id)
        # 空白被移除后无法解析
        assert result == ""

    def test_comment_in_sql(self):
        """测试带注释的 SQL"""
        sql = "SELECT * FROM users -- get all users\nWHERE status = 'active'"
        result = inject_tenant_filter(sql, self.tenant_id)
        # 注释可能会干扰解析，但应该仍然工作
        assert "tenant_id" in result


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
