"""
# 单元测试 - 数据验证器模块

## [HEADER]
**文件名**: test_data_validator.py
**职责**: 测试 data_validator.py 中的数据一致性验证和智能字段映射功能
**作者**: Data Agent Team
**版本**: 1.0.0

## [TEST CASES]
1. test_smart_field_mapping_time_series() - 时间序列数据映射
2. test_smart_field_mapping_category() - 分类数据映射
3. test_validate_consistency_with_llm_hallucination() - LLM 幻觉检测
4. test_extract_sql_columns() - SQL 列提取
5. test_infer_column_type() - 列类型推断
6. test_recommend_chart() - 图表推荐

## [LINK]
**测试目标**: [backend/src/app/services/agent/data_validator.py](../../src/app/services/agent/data_validator.py)
"""
import pytest
from backend.src.app.services.agent.data_validator import (
    DataConsistencyValidator,
    validate_sql_data_consistency,
    smart_field_mapping,
    recommend_chart,
    ColumnType,
)


class TestSmartFieldMapping:
    """测试智能字段映射功能"""

    def test_time_series_mapping(self):
        """测试时间序列数据的字段映射"""
        # 模拟销售趋势数据
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
            {"month": "2023-01", "revenue": 50000},
        ]

        mapping = smart_field_mapping(query_results)

        # 验证 X 轴是时间列
        assert mapping.x_field == "year"
        assert mapping.x_type == ColumnType.TIME

        # 验证 Y 轴是数值列
        assert mapping.y_field == "sales"
        assert mapping.y_type == ColumnType.NUMERIC

        # 验证高置信度
        assert mapping.confidence >= 0.9

    def test_category_mapping(self):
        """测试分类数据的字段映射"""
        # 模拟产品销量数据
        query_results = [
            {"product_name": "iPhone", "quantity": 500},
            {"product_name": "Samsung", "quantity": 300},
            {"product_name": "Xiaomi", "quantity": 200},
        ]

        mapping = smart_field_mapping(query_results)

        # 验证 X 轴是分类列
        assert mapping.x_field == "product_name"
        assert mapping.x_type == ColumnType.CATEGORY

        # 验证 Y 轴是数值列
        assert mapping.y_field == "quantity"
        assert mapping.y_type == ColumnType.NUMERIC

    def test_numeric_first_column_fallback(self):
        """测试第一列是数值时的回退逻辑"""
        query_results = [
            {"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob", "score": 87},
        ]

        mapping = smart_field_mapping(query_results)

        # X 轴应该是第一列（即使不是时间或分类）
        assert mapping.x_field == "id"

        # Y 轴应该是数值列
        assert mapping.y_field == "score"

    def test_empty_results(self):
        """测试空结果的处理"""
        mapping = smart_field_mapping([])

        assert mapping.x_field is None
        assert mapping.y_field is None
        assert mapping.confidence == 0.0


class TestValidateConsistency:
    """测试数据一致性验证功能"""

    def test_valid_fields(self):
        """测试有效字段的验证"""
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
        ]

        result = validate_sql_data_consistency(
            executed_sql="SELECT year, SUM(sales) FROM sales GROUP BY year",
            query_results=query_results,
            llm_config={"x_field": "year", "y_field": "sales"}
        )

        assert result.is_valid
        assert len(result.hallucinated_fields) == 0
        assert result.actual_columns == ["year", "sales"]

    def test_llm_hallucination_detection(self):
        """测试 LLM 幻觉字段的检测"""
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
        ]

        result = validate_sql_data_consistency(
            executed_sql="SELECT year, SUM(sales) FROM sales GROUP BY year",
            query_results=query_results,
            llm_config={"x_field": "product_id", "y_field": "product_name"}
        )

        # 验证检测到幻觉
        assert not result.is_valid
        assert "product_id" in result.hallucinated_fields
        assert "product_name" in result.hallucinated_fields

    def test_partial_hallucination(self):
        """测试部分幻觉（一个字段有效，一个无效）"""
        query_results = [
            {"year": 2023, "sales": 100000},
        ]

        result = validate_sql_data_consistency(
            executed_sql="SELECT year, sales FROM table",
            query_results=query_results,
            llm_config={"x_field": "year", "y_field": "invalid_field"}
        )

        # 验证只检测到无效字段
        assert not result.is_valid
        assert "invalid_field" in result.hallucinated_fields
        assert "year" not in result.hallucinated_fields

    def test_empty_query_results(self):
        """测试空查询结果"""
        result = validate_sql_data_consistency(
            executed_sql="SELECT * FROM table",
            query_results=[],
            llm_config={"x_field": "year", "y_field": "sales"}
        )

        assert not result.is_valid
        assert "查询结果为空" in result.error_message


class TestInferColumnType:
    """测试列类型推断功能"""

    def test_time_column_detection(self):
        """测试时间列检测"""
        column_name = "order_date"
        sample_data = ["2023-01-01", "2023-02-01", "2023-03-01"]

        col_type = DataConsistencyValidator.infer_column_type(column_name, sample_data)

        assert col_type == ColumnType.TIME

    def test_category_column_detection(self):
        """测试分类列检测"""
        column_name = "product_name"
        sample_data = ["iPhone", "Samsung", "Xiaomi"]

        col_type = DataConsistencyValidator.infer_column_type(column_name, sample_data)

        assert col_type == ColumnType.CATEGORY

    def test_numeric_column_detection(self):
        """测试数值列检测"""
        column_name = "total_sales"
        sample_data = [100000, 120000, 95000]

        col_type = DataConsistencyValidator.infer_column_type(column_name, sample_data)

        assert col_type == ColumnType.NUMERIC

    def test_aggregation_keywords(self):
        """测试聚合关键词检测"""
        column_name = "sum_quantity"
        sample_data = [100, 200, 300]

        col_type = DataConsistencyValidator.infer_column_type(column_name, sample_data)

        assert col_type == ColumnType.NUMERIC


class TestRecommendChart:
    """测试图表推荐功能"""

    def test_time_series_recommendation(self):
        """测试时间序列数据的图表推荐"""
        query_results = [
            {"year": 2023, "sales": 100000},
            {"year": 2024, "sales": 120000},
        ]

        recommendation = recommend_chart(
            query_results=query_results,
            executed_sql="SELECT year, SUM(sales) FROM sales GROUP BY year",
            question="展示销售趋势"
        )

        # 时间序列应该推荐折线图
        assert recommendation.chart_type == "line"
        assert recommendation.x_field == "year"
        assert recommendation.y_field == "sales"

    def test_category_comparison_recommendation(self):
        """测试分类对比的图表推荐"""
        query_results = [
            {"product_name": "iPhone", "quantity": 500},
            {"product_name": "Samsung", "quantity": 300},
        ]

        recommendation = recommend_chart(
            query_results=query_results,
            executed_sql="SELECT product_name, quantity FROM products",
            question="对比各产品销量"
        )

        # 分类对比应该推荐柱状图
        assert recommendation.chart_type in ["bar", "pie"]
        assert recommendation.x_field == "product_name"
        assert recommendation.y_field == "quantity"

    def test_question_keyword_inference(self):
        """测试基于问题关键词的推断"""
        query_results = [
            {"category": "A", "value": 30},
            {"category": "B", "value": 50},
            {"category": "C", "value": 20},
        ]

        # 占比问题
        recommendation = recommend_chart(
            query_results=query_results,
            question="各类别的占比是多少"
        )

        assert recommendation.chart_type == "pie"


class TestExtractSQLColumns:
    """测试 SQL 列提取功能"""

    def test_simple_select(self):
        """测试简单 SELECT 语句"""
        sql = "SELECT name, age, city FROM users"

        columns = DataConsistencyValidator.extract_sql_columns(sql)

        assert "name" in columns
        assert "age" in columns
        assert "city" in columns

    def test_select_with_aliases(self):
        """测试带别名的 SELECT"""
        sql = "SELECT COUNT(*) as total, YEAR(order_date) as order_year FROM orders GROUP BY order_year"

        columns = DataConsistencyValidator.extract_sql_columns(sql)

        assert "total" in columns
        assert "order_year" in columns

    def test_select_with_aggregations(self):
        """测试带聚合函数的 SELECT"""
        sql = "SELECT category, SUM(quantity) as sum_quantity, AVG(price) FROM products GROUP BY category"

        columns = DataConsistencyValidator.extract_sql_columns(sql)

        assert "category" in columns
        assert "sum_quantity" in columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
