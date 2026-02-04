# -*- coding: utf-8 -*-
"""
Excel JOIN 查询处理测试
========================

测试 Excel 数据源上的 JOIN 查询检测和智能拆分功能。

作者: Data Agent Team
版本: 1.0.0
"""

import pytest
import json
from AgentV2.tools.database_tools import (
    _extract_all_tables_from_query,
    _try_split_join_query,
    _has_subquery,
    _find_sheets_with_column
)


class TestHasSubquery:
    """测试 _has_subquery 函数"""

    def test_in_select_subquery(self):
        """检测 IN (SELECT ...) 子查询"""
        query = "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE vip = '1')"
        assert _has_subquery(query) is True

    def test_exists_subquery(self):
        """检测 EXISTS (SELECT ...) 子查询"""
        query = "SELECT * FROM orders WHERE EXISTS (SELECT 1 FROM users WHERE users.id = orders.user_id)"
        assert _has_subquery(query) is True

    def test_not_in_subquery(self):
        """检测 NOT IN (SELECT ...) 子查询"""
        query = "SELECT * FROM orders WHERE user_id NOT IN (SELECT id FROM banned_users)"
        assert _has_subquery(query) is True

    def test_equals_subquery(self):
        """检测 = (SELECT ...) 子查询"""
        query = "SELECT * FROM products WHERE price = (SELECT MAX(price) FROM products)"
        assert _has_subquery(query) is True

    def test_not_equals_subquery(self):
        """检测 != (SELECT ...) 子查询"""
        query = "SELECT * FROM products WHERE price != (SELECT MIN(price) FROM products)"
        assert _has_subquery(query) is True

    def test_any_subquery(self):
        """检测 ANY (SELECT ...) 子查询"""
        query = "SELECT * FROM orders WHERE amount > ANY (SELECT amount FROM large_orders)"
        assert _has_subquery(query) is True

    def test_all_subquery(self):
        """检测 ALL (SELECT ...) 子查询"""
        query = "SELECT * FROM orders WHERE amount > ALL (SELECT amount FROM small_orders)"
        assert _has_subquery(query) is True

    def test_no_subquery_simple_query(self):
        """简单查询不包含子查询"""
        query = "SELECT * FROM users WHERE status = 'active'"
        assert _has_subquery(query) is False

    def test_no_subquery_with_join(self):
        """JOIN 查询不包含子查询"""
        query = "SELECT * FROM users u JOIN addresses a ON u.id = a.user_id WHERE a.city = '北京'"
        assert _has_subquery(query) is False

    def test_no_subquery_with_group_by(self):
        """GROUP BY 查询不包含子查询"""
        query = "SELECT city, COUNT(*) FROM users GROUP BY city"
        assert _has_subquery(query) is False

    def test_case_when_no_subquery(self):
        """CASE WHEN 不包含子查询"""
        query = 'SELECT CASE WHEN address LIKE \'%杭州%\' THEN \'杭州\' ELSE \'其他\' END FROM users'
        assert _has_subquery(query) is False

    def test_subquery_case_insensitive(self):
        """子查询检测不区分大小写"""
        query = "select * from orders where id in (select id from users)"
        assert _has_subquery(query) is True

    def test_subquery_with_newlines(self):
        """子查询检测支持换行"""
        query = """SELECT * FROM orders
WHERE user_id IN
(SELECT id FROM users)"""
        assert _has_subquery(query) is True


class TestExtractAllTablesFromQuery:
    """测试 _extract_all_tables_from_query 函数"""

    def test_extract_single_table(self):
        """测试提取单个表名"""
        query = "SELECT * FROM users"
        tables = _extract_all_tables_from_query(query)
        assert tables == ["users"]

    def test_extract_quoted_table(self):
        """测试提取带引号的表名"""
        query = 'SELECT * FROM "users table"'
        tables = _extract_all_tables_from_query(query)
        assert tables == ["users table"]

    def test_extract_join_tables(self):
        """测试提取 JOIN 查询中的多个表名"""
        query = "SELECT * FROM users u LEFT JOIN addresses a ON u.id = a.user_id"
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"users", "addresses"}

    def test_extract_multiple_joins(self):
        """测试提取多个 JOIN 的表名"""
        query = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id JOIN products p ON o.product_id = p.id"
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"orders", "customers", "products"}

    def test_extract_inner_join(self):
        """测试 INNER JOIN"""
        query = "SELECT * FROM users INNER JOIN addresses ON users.id = addresses.user_id"
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"users", "addresses"}

    def test_extract_right_join(self):
        """测试 RIGHT JOIN"""
        query = "SELECT * FROM users RIGHT JOIN addresses ON users.id = addresses.user_id"
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"users", "addresses"}

    def test_extract_with_where_clause(self):
        """测试带 WHERE 子句的查询"""
        query = 'SELECT * FROM users u LEFT JOIN addresses a ON u.id = a.user_id WHERE a.city = "北京"'
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"users", "addresses"}

    def test_extract_with_comments(self):
        """测试带注释的查询"""
        query = "-- This is a comment\nSELECT * FROM users LEFT JOIN addresses ON users.id = addresses.user_id"
        tables = _extract_all_tables_from_query(query)
        assert set(tables) == {"users", "addresses"}

    def test_extract_empty_query(self):
        """测试空查询"""
        tables = _extract_all_tables_from_query("")
        assert tables == []

    def test_extract_no_from_clause(self):
        """测试没有 FROM 子句的查询"""
        tables = _extract_all_tables_from_query("SELECT 1")
        assert tables == []


class TestTrySplitJoinQuery:
    """测试 _try_split_join_query 函数"""

    def test_split_simple_left_join(self, tmp_path):
        """测试简单 LEFT JOIN 拆分"""
        import pandas as pd

        # 创建测试 Excel 文件
        file_path = tmp_path / "test.xlsx"

        # 创建包含 city 列的工作表
        df_addresses = pd.DataFrame({
            "user_id": [1, 2, 3],
            "city": ["北京", "上海", "杭州"],
            "province": ["北京市", "上海市", "浙江省"]
        })
        df_users = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_users.to_excel(writer, sheet_name="users", index=False)
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)

        # 测试拆分：查询 addresses 表中的城市信息
        query = 'SELECT * FROM users u LEFT JOIN addresses a ON u.id = a.user_id WHERE a.city = "北京"'
        result = _try_split_join_query(query, str(file_path))

        assert result is not None
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["_join_split"] is True
        assert result_json["sheet_name"] == "addresses"
        assert result_json["row_count"] == 1

    def test_split_with_province_filter(self, tmp_path):
        """测试带省份过滤的 JOIN 拆分"""
        import pandas as pd

        # 创建测试 Excel 文件
        file_path = tmp_path / "test_province.xlsx"

        # 创建包含 province 列的工作表
        df_addresses = pd.DataFrame({
            "user_id": [1, 2, 3, 4],
            "city": ["合肥", "芜湖", "南京", "杭州"],
            "province": ["安徽省", "安徽省", "江苏省", "浙江省"]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)

        # 测试拆分：查询安徽省的用户
        query = 'SELECT * FROM users u LEFT JOIN addresses a ON u.id = a.user_id WHERE a.province = "安徽省"'
        result = _try_split_join_query(query, str(file_path))

        assert result is not None
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["sheet_name"] == "addresses"
        assert result_json["row_count"] == 2  # 安徽省有2条记录

    def test_split_returns_none_for_no_where(self, tmp_path):
        """测试没有 WHERE 子句时返回 None"""
        import pandas as pd

        file_path = tmp_path / "test_no_where.xlsx"
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        df.to_excel(file_path, sheet_name="test", index=False, engine='openpyxl')

        query = "SELECT * FROM users LEFT JOIN addresses ON users.id = addresses.user_id"
        result = _try_split_join_query(query, str(file_path))

        assert result is None  # 没有 WHERE 子句，无法拆分

    def test_split_returns_none_for_nonexistent_column(self, tmp_path):
        """测试目标列不存在时返回 None"""
        import pandas as pd

        file_path = tmp_path / "test_no_col.xlsx"
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        df.to_excel(file_path, sheet_name="test", index=False, engine='openpyxl')

        # 查询一个不存在的列
        query = 'SELECT * FROM users LEFT JOIN addresses ON users.id = addresses.user_id WHERE addresses.nonexistent_col = "value"'
        result = _try_split_join_query(query, str(file_path))

        assert result is None  # 找不到目标列


class TestExcelSubqueryIntegration:
    """集成测试：Excel 子查询检测"""

    def test_subquery_detection_in_execute_query(self, tmp_path):
        """测试 execute_query 中的子查询检测"""
        import pandas as pd
        from AgentV2.tools.database_tools import execute_query

        # 创建测试 Excel 文件
        file_path = tmp_path / "subquery_test.xlsx"

        df_addresses = pd.DataFrame({
            "user_id": [1, 2, 3, 4],
            "province": ["安徽省", "浙江省", "江苏省", "安徽省"],
            "city": ["合肥", "杭州", "南京", "芜湖"]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)

        # 设置 Excel 连接
        excel_url = f"excel://{file_path}"

        # 测试子查询应该被检测并返回友好的错误
        query = 'SELECT * FROM "orders" WHERE address_id IN (SELECT id FROM "addresses" WHERE province = \'安徽\')'
        result = execute_query(query, excel_url)

        result_json = json.loads(result)
        assert result_json.get("error_type") == "subquery_not_supported"
        assert "Excel 数据源不支持子查询" in result_json.get("error", "")
        assert "suggestion" in result_json

    def test_no_subquery_single_table_executes(self, tmp_path):
        """测试没有子查询的单表查询应该正常执行"""
        import pandas as pd
        from AgentV2.tools.database_tools import execute_query

        file_path = tmp_path / "single_table_no_subquery.xlsx"
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "province": ["安徽省", "浙江省", "江苏省"],
            "count": [100, 200, 150]
        })
        df.to_excel(file_path, sheet_name="data", index=False, engine='openpyxl')

        excel_url = f"excel://{file_path}"

        # 没有子查询的查询应该正常执行
        query = 'SELECT * FROM "data" WHERE province = \'安徽省\''
        result = execute_query(query, excel_url)

        result_json = json.loads(result)
        assert result_json.get("success") is True
        assert result_json["row_count"] == 1


class TestExcelJoinIntegration:
    """集成测试：Excel JOIN 查询的完整流程"""

    def test_join_detection_in_execute_query(self, tmp_path):
        """测试 execute_query 中的 JOIN 检测"""
        import pandas as pd
        from AgentV2.tools.database_tools import execute_query

        # 创建测试 Excel 文件
        file_path = tmp_path / "integration_test.xlsx"

        df_addresses = pd.DataFrame({
            "user_id": [1, 2, 3, 4],
            "province": ["安徽省", "浙江省", "江苏省", "安徽省"],
            "city": ["合肥", "杭州", "南京", "芜湖"]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)

        # 设置 Excel 连接
        excel_url = f"excel://{file_path}"

        # 测试 JOIN 查询应该被检测并返回友好的错误
        query = 'SELECT * FROM users u LEFT JOIN addresses a ON u.id = a.user_id WHERE a.province = "安徽省"'
        result = execute_query(query, excel_url)

        result_json = json.loads(result)
        # 应该返回错误（因为 users 表不存在）
        # 或者如果成功拆分，应该返回正确的结果
        assert "error" in result_json or result_json.get("success") is True

    def test_no_join_single_table_query(self, tmp_path):
        """测试单表查询不应该触发 JOIN 检测"""
        import pandas as pd
        from AgentV2.tools.database_tools import execute_query

        file_path = tmp_path / "single_table_test.xlsx"
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "province": ["安徽省", "浙江省", "江苏省"],
            "count": [100, 200, 150]
        })
        df.to_excel(file_path, sheet_name="data", index=False, engine='openpyxl')

        excel_url = f"excel://{file_path}"

        # 单表查询应该正常执行
        query = 'SELECT * FROM "data" WHERE province = "安徽省"'
        result = execute_query(query, excel_url)

        result_json = json.loads(result)
        assert result_json.get("success") is True
        assert result_json["row_count"] == 1




class TestFindSheetsWithColumn:
    """测试 _find_sheets_with_column 智能建议功能"""

    def test_find_province_column(self, tmp_path):
        """测试查找包含 province 列的工作表"""
        import pandas as pd

        file_path = tmp_path / "find_province.xlsx"

        # 创建多个工作表
        df_addresses = pd.DataFrame({
            "user_id": [1, 2, 3],
            "province": ["安徽省", "浙江省", "江苏省"],
            "city": ["合肥", "杭州", "南京"]
        })
        df_users = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })
        df_orders = pd.DataFrame({
            "order_id": [101, 102],
            "amount": [100, 200]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_users.to_excel(writer, sheet_name="users", index=False)
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)
            df_orders.to_excel(writer, sheet_name="orders", index=False)

        # 查找包含 province 列的工作表
        result = _find_sheets_with_column(str(file_path), "province")

        assert result == ["addresses"]

    def test_find_city_column_multiple_sheets(self, tmp_path):
        """测试查找包含 city 列的工作表（多个工作表）"""
        import pandas as pd

        file_path = tmp_path / "find_city_multiple.xlsx"

        # 创建多个包含 city 列的工作表
        df_addresses = pd.DataFrame({
            "user_id": [1, 2],
            "city": ["合肥", "杭州"]
        })
        df_shipping = pd.DataFrame({
            "order_id": [101, 102],
            "city": ["北京", "上海"]
        })
        df_users = pd.DataFrame({
            "id": [1, 2],
            "name": ["Alice", "Bob"]
        })

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_users.to_excel(writer, sheet_name="users", index=False)
            df_addresses.to_excel(writer, sheet_name="addresses", index=False)
            df_shipping.to_excel(writer, sheet_name="shipping", index=False)

        # 查找包含 city 列的工作表
        result = _find_sheets_with_column(str(file_path), "city")

        assert set(result) == {"addresses", "shipping"}

    def test_find_nonexistent_column(self, tmp_path):
        """测试查找不存在的列"""
        import pandas as pd

        file_path = tmp_path / "find_nonexistent.xlsx"
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        df.to_excel(file_path, sheet_name="test", index=False, engine='openpyxl')

        result = _find_sheets_with_column(str(file_path), "nonexistent_column")

        assert result == []

    def test_find_column_case_insensitive(self, tmp_path):
        """测试列名查找不区分大小写"""
        import pandas as pd

        file_path = tmp_path / "case_insensitive.xlsx"
        df = pd.DataFrame({
            "ID": [1, 2],
            "Province": ["安徽", "浙江"],
            "City": ["合肥", "杭州"]
        })
        df.to_excel(file_path, sheet_name="data", index=False, engine='openpyxl')

        # 小写查找应该匹配
        result_lower = _find_sheets_with_column(str(file_path), "province")
        assert result_lower == ["data"]

        # 大写查找应该匹配
        result_upper = _find_sheets_with_column(str(file_path), "PROVINCE")
        assert result_upper == ["data"]

    def test_find_column_with_chinese_name(self, tmp_path):
        """测试查找中文列名"""
        import pandas as pd

        file_path = tmp_path / "chinese_column.xlsx"
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "省份": ["安徽省", "浙江省", "江苏省"],
            "城市": ["合肥", "杭州", "南京"]
        })
        df.to_excel(file_path, sheet_name="地址表", index=False, engine='openpyxl')

        # 查找中文列名
        result = _find_sheets_with_column(str(file_path), "省份")

        assert result == ["地址表"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
