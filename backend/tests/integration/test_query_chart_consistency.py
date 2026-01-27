"""
# 集成测试 - 查询与图表一致性测试

## [HEADER]
**文件名**: test_query_chart_consistency.py
**职责**: 测试完整的查询流程中 SQL 执行结果与图表配置的一致性
**作者**: Data Agent Team
**版本**: 1.0.0

## [TEST CASES]
1. test_sales_trend_query_consistency() - 销售趋势查询一致性
2. test_category_comparison_consistency() - 分类对比一致性
3. test_hallucination_prevention() - 幻觉预防测试
4. test_empty_query_results() - 空查询结果处理
5. test_multi_column_results() - 多列结果处理

## [LINK]
**测试目标**:
- [backend/src/app/services/agent/agent_service.py](../../src/app/services/agent/agent_service.py)
- [backend/src/app/services/agent/data_validator.py](../../src/app/services/agent/data_validator.py)
- [backend/src/app/services/agent/data_transformer.py](../../src/app/services/agent/data_transformer.py)
"""
import pytest
from backend.src.app.services.agent.data_validator import (
    validate_sql_data_consistency,
    smart_field_mapping,
    recommend_chart,
)
from backend.src.app.services.agent.data_transformer import prepare_mcp_chart_request
from backend.src.app.services.agent.models import ChartType


class TestSalesTrendConsistency:
    """销售趋势查询的一致性测试"""

    def test_year_over_year_sales(self):
        """测试年度销售对比查询的一致性"""
        # 模拟 SQL 执行结果
        query_results = [
            {"year": 2023, "total_sales": 1000000},
            {"year": 2024, "total_sales": 1200000},
        ]
        executed_sql = "SELECT year, SUM(sales) as total_sales FROM orders GROUP BY year ORDER BY year"

        # 验证数据一致性
        validation = validate_sql_data_consistency(executed_sql, query_results)
        assert validation.is_valid
        assert "year" in validation.actual_columns
        assert "total_sales" in validation.actual_columns

        # 验证智能字段映射
        field_mapping = smart_field_mapping(query_results, executed_sql)
        assert field_mapping.x_field == "year"
        assert field_mapping.y_field == "total_sales"

        # 验证图表推荐
        chart_rec = recommend_chart(query_results, executed_sql, "对比2023和2024年的销售额")
        assert chart_rec.chart_type in ["bar", "line"]  # 对比查询应推荐 bar 或 line

        # 验证图表配置生成
        _, chart_config, echarts_option = prepare_mcp_chart_request(
            sql_result=query_results,
            sql=executed_sql,
            x_field=field_mapping.x_field,
            y_field=field_mapping.y_field,
            chart_type=chart_rec.chart_type,
        )

        assert chart_config.x_field == "year"
        assert chart_config.y_field == "total_sales"
        assert echarts_option is not None

    def test_monthly_sales_trend(self):
        """测试月度销售趋势查询的一致性"""
        query_results = [
            {"month": "2023-01", "revenue": 80000},
            {"month": "2023-02", "revenue": 95000},
            {"month": "2023-03", "revenue": 110000},
        ]
        executed_sql = "SELECT DATE_FORMAT(order_date, '%Y-%m') as month, SUM(amount) as revenue FROM orders GROUP BY month"

        # 验证图表推荐（时间序列应推荐折线图）
        chart_rec = recommend_chart(query_results, executed_sql, "展示月度销售趋势")
        assert chart_rec.chart_type == "line"

        # 验证字段映射
        field_mapping = smart_field_mapping(query_results, executed_sql)
        assert field_mapping.x_field == "month"
        assert field_mapping.y_field == "revenue"


class TestCategoryComparisonConsistency:
    """分类对比查询的一致性测试"""

    def test_product_sales_comparison(self):
        """测试产品销量对比查询的一致性"""
        query_results = [
            {"product_name": "iPhone 15", "quantity": 500},
            {"product_name": "Samsung S24", "quantity": 350},
            {"product_name": "Xiaomi 14", "quantity": 280},
        ]
        executed_sql = "SELECT product_name, COUNT(*) as quantity FROM orders GROUP BY product_name ORDER BY quantity DESC"

        # 验证智能字段映射
        field_mapping = smart_field_mapping(query_results, executed_sql)
        assert field_mapping.x_field == "product_name"
        assert field_mapping.y_field == "quantity"

        # 验证图表推荐（分类对比应推荐柱状图）
        chart_rec = recommend_chart(query_results, executed_sql, "对比各产品销量排名")
        assert chart_rec.chart_type == "bar"

    def test_category_distribution(self):
        """测试分类分布查询的一致性"""
        query_results = [
            {"category": "Electronics", "order_count": 150},
            {"category": "Clothing", "order_count": 120},
            {"category": "Food", "order_count": 80},
        ]
        executed_sql = "SELECT category, COUNT(*) as order_count FROM products GROUP BY category"

        # 验证图表推荐（分布查询且类别少应推荐饼图）
        chart_rec = recommend_chart(query_results, executed_sql, "各类别的订单占比")
        assert chart_rec.chart_type == "pie"


class TestHallucinationPrevention:
    """幻觉预防测试"""

    def test_reject_nonexistent_fields(self):
        """测试拒绝不存在的字段"""
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
        ]

        # 模拟 LLM 幻觉 - 提供不存在的字段
        llm_config = {"x_field": "product_id", "y_field": "product_name"}

        validation = validate_sql_data_consistency(
            executed_sql="SELECT year, sales FROM table",
            query_results=query_results,
            llm_config=llm_config
        )

        assert not validation.is_valid
        assert "product_id" in validation.hallucinated_fields
        assert "product_name" in validation.hallucinated_fields

    def test_field_validation_in_chart_request(self):
        """测试图表请求中的字段验证"""
        query_results = [
            {"year": 2023, "sales": 100000},
        ]

        # 尝试使用不存在的字段生成图表
        _, chart_config, _ = prepare_mcp_chart_request(
            sql_result=query_results,
            sql="SELECT year, sales FROM table",
            x_field="invalid_field",  # 不存在的字段
            y_field="another_invalid",  # 不存在的字段
        )

        # 验证实际使用的字段是存在的
        assert chart_config.x_field in query_results[0].keys()
        assert chart_config.y_field in query_results[0].keys()

    def test_mixed_valid_invalid_fields(self):
        """测试混合有效和无效字段的情况"""
        query_results = [
            {"year": 2023, "sales": 100000},
        ]

        # X 字段有效，Y 字段无效
        _, chart_config, _ = prepare_mcp_chart_request(
            sql_result=query_results,
            sql="SELECT year, sales FROM table",
            x_field="year",  # 有效
            y_field="revenue",  # 无效
        )

        assert chart_config.x_field == "year"
        # Y 字段应该回退到可用字段
        assert chart_config.y_field is not None
        assert chart_config.y_field in query_results[0].keys()


class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_query_results(self):
        """测试空查询结果的处理"""
        query_results = []

        field_mapping = smart_field_mapping(query_results)
        assert field_mapping.x_field is None
        assert field_mapping.y_field is None

        chart_rec = recommend_chart(query_results)
        assert chart_rec.chart_type == "table"

    def test_single_column_result(self):
        """测试单列结果的处理"""
        query_results = [{"total": 1000}]

        field_mapping = smart_field_mapping(query_results)
        # 单列无法生成有意义的图表
        assert field_mapping.x_field == "total"
        assert field_mapping.y_field is None

    def test_large_result_set(self):
        """测试大数据集的处理"""
        # 生成大量数据
        query_results = [
            {"month": f"2023-{i:02d}", "sales": i * 10000}
            for i in range(1, 13)
        ]

        chart_rec = recommend_chart(query_results, question="月度销售趋势")
        # 时间序列大数据集应推荐折线图
        assert chart_rec.chart_type == "line"

    def test_all_numeric_columns(self):
        """测试全是数值列的情况"""
        query_results = [
            {"id": 1, "value1": 100, "value2": 200},
            {"id": 2, "value1": 150, "value2": 250},
        ]

        field_mapping = smart_field_mapping(query_results)
        # 应该选择第一列作为 X 轴
        assert field_mapping.x_field == "id"
        # Y 轴应该是其他数值列之一
        assert field_mapping.y_field in ["value1", "value2"]


class TestDataIntegrity:
    """数据完整性测试"""

    def test_chart_data_matches_table_data(self):
        """测试图表数据与表格数据的一致性"""
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
        ]

        field_mapping = smart_field_mapping(query_results)
        _, chart_config, echarts_option = prepare_mcp_chart_request(
            sql_result=query_results,
            sql="SELECT year, sales FROM table",
            x_field=field_mapping.x_field,
            y_field=field_mapping.y_field,
            chart_type="bar",
        )

        # 验证图表配置中的字段与查询结果匹配
        assert chart_config.x_field in query_results[0].keys()
        assert chart_config.y_field in query_results[0].keys()

        # 验证 ECharts 配置包含正确的数据
        if echarts_option:
            assert "series" in echarts_option
            assert len(echarts_option["series"]) > 0

    def test_preserve_data_types(self):
        """测试数据类型保持正确"""
        query_results = [
            {"category": "A", "value": "100.5"},  # 字符串形式的数值
            {"category": "B", "value": "200.7"},
        ]

        _, chart_config, echarts_option = prepare_mcp_chart_request(
            sql_result=query_results,
            sql="SELECT category, value FROM table",
            chart_type="bar",
        )

        # 验证数值类型被正确转换
        if echarts_option and echarts_option.get("series"):
            series_data = echarts_option["series"][0].get("data", [])
            # 数据应该是数值类型
            for item in series_data:
                if isinstance(item, list) and len(item) >= 2:
                    assert isinstance(item[1], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
