# -*- coding: utf-8 -*-
"""
占比查询 SQL 修正器测试套件

测试覆盖率目标：
1. SQL 模式检测测试
2. SQL 修正逻辑测试
3. 边界情况测试
"""

import pytest
import sys
import os

# 添加父目录到路径以导入 sql_validator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sql_validator import SQLValidator


class TestProportionSQLDetection:
    """测试占比类查询的检测逻辑"""

    def test_detect_province_proportion_query(self):
        """测试检测省份占比查询"""
        # Given: 错误的 SQL 和包含占比关键词的用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古'"
        user_query = "内蒙古客户占比"

        # When: 调用 SQL 修正器
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回修正后的 SQL
        assert "GROUP BY province" in fixed_sql
        assert fixed_sql != sql

    def test_detect_city_proportion_query(self):
        """测试检测城市占比查询"""
        # Given: 错误的 SQL 和包含占比关键词的用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE city = '北京'"
        user_query = "北京客户占比"

        # When: 调用 SQL 修正器
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回修正后的 SQL
        assert "GROUP BY city" in fixed_sql
        assert fixed_sql != sql

    def test_no_fix_for_non_proportion_query(self):
        """测试非占比查询不修正"""
        # Given: 普通 SQL 和没有占比关键词的用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古'"
        user_query = "内蒙古有多少客户"

        # When: 调用 SQL 修正器
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回原始 SQL（不修正）
        assert fixed_sql == sql

    def test_no_fix_when_group_by_exists(self):
        """测试已有 GROUP BY 的查询不修正"""
        # Given: 正确的 SQL
        sql = "SELECT province, COUNT(*) as count FROM addresses GROUP BY province"
        user_query = "各省份客户占比"

        # When: 调用 SQL 修正器
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回原始 SQL（不修正）
        assert fixed_sql == sql

    def test_detect_distribution_keyword(self):
        """测试检测分布关键词"""
        # Given: 错误的 SQL 和包含分布关键词的用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '安徽'"
        user_query = "客户省份分布"

        # When: 调用 SQL 修正器
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回修正后的 SQL
        assert "GROUP BY province" in fixed_sql
        assert fixed_sql != sql


class TestProportionSQLFixing:
    """测试 SQL 修正逻辑"""

    def test_fix_province_where_clause(self):
        """测试修正省份 WHERE 子句"""
        # Given: 错误的 SQL
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古'"
        user_query = "内蒙古客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该生成正确的 GROUP BY 查询
        assert "SELECT province" in fixed_sql
        assert "COUNT(*) as count" in fixed_sql.lower() or "count(*)" in fixed_sql.lower()
        assert "GROUP BY province" in fixed_sql
        assert "ORDER BY count DESC" in fixed_sql

    def test_fix_city_where_clause(self):
        """测试修正城市 WHERE 子句"""
        # Given: 错误的 SQL
        sql = "SELECT COUNT(*) FROM addresses WHERE city = '上海'"
        user_query = "上海客户比例"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该生成正确的 GROUP BY 查询
        assert "SELECT city" in fixed_sql
        assert "GROUP BY city" in fixed_sql
        assert "ORDER BY count DESC" in fixed_sql

    def test_fix_preserves_table_name(self):
        """测试修正时保留表名"""
        # Given: 错误的 SQL（使用 users 表）
        sql = "SELECT COUNT(*) FROM users WHERE province = '浙江'"
        user_query = "浙江客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该保留原表名
        assert "FROM users" in fixed_sql or "from users" in fixed_sql.lower()

    def test_fix_with_customers_table(self):
        """测试修正 customers 表的查询"""
        # Given: 错误的 SQL（使用 customers 表）
        sql = "SELECT COUNT(*) FROM customers WHERE province = '江苏'"
        user_query = "江苏客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该保留 customers 表名
        assert "FROM customers" in fixed_sql or "from customers" in fixed_sql.lower()
        assert "GROUP BY province" in fixed_sql


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_sql(self):
        """测试空 SQL"""
        # Given: 空 SQL
        sql = ""
        user_query = "内蒙古客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回空字符串
        assert fixed_sql == ""

    def test_none_sql(self):
        """测试 None SQL"""
        # Given: None SQL
        sql = None
        user_query = "内蒙古客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回 None
        assert fixed_sql is None

    def test_whitespace_only_sql(self):
        """测试仅包含空格的 SQL"""
        # Given: 仅空格的 SQL
        sql = "   "
        user_query = "内蒙古客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回原始 SQL
        assert fixed_sql == sql

    def test_empty_user_query(self):
        """测试空用户查询"""
        # Given: SQL 和空用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古'"
        user_query = ""

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该返回原始 SQL（不修正）
        assert fixed_sql == sql

    def test_complex_where_clause(self):
        """测试复杂 WHERE 子句（可能不修正）"""
        # Given: 带 LIMIT 的 SQL
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古' LIMIT 10"
        user_query = "内蒙古客户占比"

        # When: 修正 SQL（有 LIMIT，可能跳过修正）
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 根据 LIMIT 检查逻辑决定是否修正
        # 当前实现中，带 LIMIT 的查询不会被通用模式修正
        # 但会被特定模式修正
        if "GROUP BY" in fixed_sql:
            # 被特定模式修正了
            assert "GROUP BY province" in fixed_sql
        else:
            # 没被修正（因为 LIMIT）
            assert fixed_sql == sql

    def test_case_insensitive_detection(self):
        """测试大小写不敏感的检测"""
        # Given: 大写的 SQL
        sql = "SELECT COUNT(*) FROM ADDRESSES WHERE PROVINCE = '内蒙古'"
        user_query = "内蒙古客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该能检测并修正
        assert "GROUP BY" in fixed_sql.upper()
        assert fixed_sql != sql


class TestCommonProvinces:
    """测试常见省份名称"""

    provinces = ['内蒙古', '安徽', '浙江', '江苏', '上海', '北京', '广东', '山东', '河南', '湖北']

    @pytest.mark.parametrize("province", provinces)
    def test_fix_for_common_provinces(self, province):
        """测试修正常见省份的查询"""
        # Given: 针对不同省份的错误 SQL
        sql = f"SELECT COUNT(*) FROM addresses WHERE province = '{province}'"
        user_query = f"{province}客户占比"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该生成 GROUP BY 查询
        assert "GROUP BY province" in fixed_sql
        assert fixed_sql != sql


class TestPercentageKeywords:
    """测试不同的占比关键词"""

    keywords = ['占比', '比例', '分布', '百分比', '多少']

    @pytest.mark.parametrize("keyword", keywords)
    def test_detect_percentage_keywords(self, keyword):
        """测试检测不同的占比关键词"""
        # Given: 包含不同关键词的用户查询
        sql = "SELECT COUNT(*) FROM addresses WHERE province = '内蒙古'"
        user_query = f"内蒙古客户{keyword}"

        # When: 修正 SQL
        fixed_sql = SQLValidator.fix_proportion_sql(sql, user_query)

        # Then: 应该检测到并修正
        assert "GROUP BY province" in fixed_sql
        assert fixed_sql != sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
