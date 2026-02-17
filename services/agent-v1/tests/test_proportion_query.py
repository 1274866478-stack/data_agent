"""
占比查询优化测试套件

测试覆盖率目标：
1. 数值一致性测试
2. 饼图数据转换测试
3. 步骤过滤测试
"""

import pytest
from typing import List, Dict, Any, Optional
from models import QueryResult
from sql_agent import (
    _analyze_numeric_data,
    validate_answer_consistency,
    extract_percentage_from_answer,
    calculate_proportion_from_data,
    supplement_proportion_data,
    filter_user_friendly_steps
)


class TestProportionCalculation:
    """测试占比计算一致性"""

    def test_calculate_proportion_from_data(self):
        """测试从数据计算占比"""
        # Given: 模拟查询结果
        data = [
            {"region": "内蒙古", "count": 140},
            {"region": "其他", "count": 860}
        ]
        columns = ["region", "count"]

        # When: 计算占比
        result = calculate_proportion_from_data(data, columns, "内蒙古")

        # Then: 应该得到正确的占比
        assert result["target_value"] == 140
        assert result["total"] == 1000
        assert result["percentage"] == 14.0

    def test_calculate_proportion_with_single_row(self):
        """测试单行数据的占比计算（需要总计）"""
        # Given: 单行数据
        data = [{"region": "内蒙古", "count": 140}]
        columns = ["region", "count"]

        # When: 计算占比（需要提供 total）
        result = calculate_proportion_from_data(
            data, columns, "内蒙古", total=1000
        )

        # Then: 应该得到正确的占比
        assert result["percentage"] == 14.0

    def test_extract_percentage_from_answer(self):
        """测试从答案中提取百分比"""
        # Given: 包含百分比的答案
        answer = "根据查询结果，内蒙古客户占比为 14%，约 3.4% 的用户"

        # When: 提取百分比
        percentages = extract_percentage_from_answer(answer)

        # Then: 应该提取到所有百分比
        assert len(percentages) >= 1
        assert 14.0 in percentages

    def test_validate_answer_consistency_match(self):
        """测试答案一致性校验 - 匹配情况"""
        # Given: SQL 结果和一致的答案
        sql_result = {"target_value": 140, "total": 1000, "percentage": 14.0}
        llm_answer = "内蒙古客户占比为 14%"

        # When: 校验一致性
        result = validate_answer_consistency(sql_result, llm_answer)

        # Then: 应该一致
        assert result["is_consistent"] == True

    def test_validate_answer_consistency_mismatch(self):
        """测试答案一致性校验 - 不匹配情况"""
        # Given: SQL 结果和不一致的答案
        sql_result = {"target_value": 140, "total": 1000, "percentage": 14.0}
        llm_answer = "内蒙古客户占比为 3.4%"

        # When: 校验一致性
        result = validate_answer_consistency(sql_result, llm_answer)

        # Then: 应该不一致，并提供修正后的答案
        assert result["is_consistent"] == False
        assert "14.0%" in result["corrected_answer"] or "14%" in result["corrected_answer"]


class TestPieChartTransformation:
    """测试饼图数据转换"""

    def test_supplement_proportion_data_single_point(self):
        """测试单点数据自动补全为双点"""
        # Given: 单点数据
        data = [{"category": "内蒙古", "value": 140}]
        total = 1000

        # When: 补全数据
        result = supplement_proportion_data(data, total=total)

        # Then: 应该有两个数据点
        assert len(result) == 2
        assert result[0]["category"] == "内蒙古"
        assert result[0]["value"] == 140
        assert result[1]["category"] == "其他"
        assert result[1]["value"] == 860

    def test_supplement_proportion_data_multiple_points(self):
        """测试多点数据不需要补全"""
        # Given: 多点数据
        data = [
            {"category": "内蒙古", "value": 140},
            {"category": "北京", "value": 300},
            {"category": "上海", "value": 560}
        ]

        # When: 补全数据
        result = supplement_proportion_data(data)

        # Then: 应该保持原样
        assert len(result) == 3

    def test_supplement_proportion_data_zero_total(self):
        """测试总计为零的边缘情况"""
        # Given: 单点数据且总为零
        data = [{"category": "内蒙古", "value": 0}]

        # When: 补全数据
        result = supplement_proportion_data(data, total=0)

        # Then: 应该有补全数据
        assert len(result) == 2
        assert result[1]["value"] == 0


class TestStepFiltering:
    """测试步骤过滤"""

    def test_filter_technical_steps(self):
        """测试技术步骤被过滤"""
        # Given: 包含技术步骤的完整步骤列表
        all_steps = [
            {"step": 1, "node": "list_tables", "title": "获取表列表"},
            {"step": 2, "node": "get_schema", "title": "获取表结构"},
            {"step": 3, "node": "query", "title": "执行查询"},
            {"step": 4, "node": "analysis", "title": "数据分析"}
        ]

        # When: 过滤步骤
        visible = filter_user_friendly_steps(all_steps)

        # Then: 技术步骤应被过滤
        assert len(visible) == 2
        assert all(s["node"] not in ["list_tables", "get_schema"] for s in visible)

    def test_filter_preserves_business_steps(self):
        """测试业务步骤被保留"""
        # Given: 步骤列表
        all_steps = [
            {"step": 1, "node": "query", "title": "执行查询"},
            {"step": 2, "node": "analysis", "title": "数据分析"},
            {"step": 3, "node": "visualization", "title": "生成图表"}
        ]

        # When: 过滤步骤
        visible = filter_user_friendly_steps(all_steps)

        # Then: 所有业务步骤应被保留
        assert len(visible) == 3


class TestNumericAnalysis:
    """测试数值分析增强"""

    def test_analyze_with_proportion_keywords(self):
        """测试检测占比关键词时的分析"""
        # Given: 包含占比查询的数据
        rows = [[140], [860]]
        columns = ["count"]

        # When: 分析数据
        result = _analyze_numeric_data(rows, columns, is_proportion_query=True)

        # Then: 应该包含占比信息
        assert "占比" in result or "14%" in result

    def test_analyze_calculation_formula(self):
        """测试计算公式的显示"""
        # Given: 数据 - 使用字典格式以支持类别匹配
        rows = [[140], [860]]
        columns = ["count"]

        # When: 分析数据（不指定target_name，使用常规统计）
        result = _analyze_numeric_data(rows, columns)

        # Then: 应该显示统计信息
        assert "总计" in result or "1000" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
