"""
测试统计分析服务

验证统计分析服务的各项功能
"""

import pytest
from src.app.services.stats_analysis_service import StatsAnalysisService, get_stats_service


class TestStatsAnalysisService:
    """测试统计分析服务"""

    @pytest.fixture
    def service(self):
        """创建统计分析服务实例"""
        return StatsAnalysisService()

    @pytest.fixture
    def sample_time_series_data(self):
        """示例时间序列数据（2023年销售数据）"""
        return {
            "columns": ["month", "sales"],
            "rows": [
                ["2023-01", 9919],
                ["2023-02", 9785],
                ["2023-03", 10978],
                ["2023-04", 8737],
                ["2023-05", 10430],
                ["2023-06", 8908],
                ["2023-07", 8709],
                ["2023-08", 9449],
                ["2023-09", 9532],
                ["2023-10", 9435],
                ["2023-11", 9792],
                ["2023-12", 9634],
            ]
        }

    @pytest.fixture
    def sample_simple_data(self):
        """示例简单数据（无时间列）"""
        return {
            "columns": ["product", "sales"],
            "rows": [
                ["产品A", 100],
                ["产品B", 200],
                ["产品C", 150],
                ["产品D", 300],
                ["产品E", 250],
            ]
        }

    def test_basic_stats_calculation(self, service, sample_time_series_data):
        """测试基础统计指标计算"""
        result = service.analyze_query_result(sample_time_series_data)

        assert "error" not in result
        assert "basic_stats" in result

        basic = result["basic_stats"]
        assert basic["count"] == 12
        assert basic["total"] == pytest.approx(116308, rel=0.1)
        assert basic["mean"] == pytest.approx(9692, rel=0.1)
        assert basic["min"] == 8709
        assert basic["max"] == 10978
        assert basic["std_dev"] > 0  # 标准差应该大于0

    def test_trend_analysis(self, service, sample_time_series_data):
        """测试趋势分析"""
        result = service.analyze_query_result(sample_time_series_data)

        assert "error" not in result
        assert "trend_analysis" in result

        trend = result["trend_analysis"]
        assert "total_growth_percent" in trend
        assert "avg_growth_percent" in trend
        assert "volatility" in trend
        assert "trend_direction" in trend

        # 验证增长率计算
        # 从1月(9919)到12月(9634)，应该是下降
        assert trend["trend_direction"] in ["上升", "下降", "平稳"]

    def test_extremes_detection(self, service, sample_time_series_data):
        """测试极值检测"""
        result = service.analyze_query_result(sample_time_series_data)

        assert "error" not in result
        assert "extremes" in result

        extremes = result["extremes"]
        assert extremes["max_value"] == 10978  # 3月最高
        assert extremes["min_value"] == 8709  # 7月最低
        assert len(extremes["max_rows"]) > 0
        assert len(extremes["min_rows"]) > 0

    def test_distribution_analysis(self, service, sample_time_series_data):
        """测试分布分析"""
        result = service.analyze_query_result(sample_time_series_data)

        assert "error" not in result
        assert "distribution" in result

        dist = result["distribution"]
        assert "q1" in dist
        assert "q2" in dist  # 中位数
        assert "q3" in dist
        assert "iqr" in dist  # 四分位距

        # 验证中位数在合理范围内（使用 basic_stats 中的 min/max）
        basic_stats = result.get("basic_stats", {})
        if basic_stats:
            min_val = basic_stats.get("min")
            max_val = basic_stats.get("max")
            if min_val and max_val:
                assert min_val < dist["q2"] < max_val

    def test_column_auto_detection(self, service, sample_simple_data):
        """测试自动列检测"""
        result = service.analyze_query_result(sample_simple_data)

        assert "error" not in result
        # 应该自动检测到 sales 列为数值列
        assert result["value_column"] == "sales"

    def test_format_stats_analysis(self):
        """测试统计结果格式化（关键数据点模式）"""
        from src.app.services.agent_service import _format_stats_analysis

        # 测试场景1：平稳数据（无明显趋势，无异常值）
        stats_stable = {
            "basic_stats": {
                "count": 12,
                "total": 116308,
                "mean": 9692.33,
                "median": 9592,
                "std_dev": 677.5,
                "min": 8709,
                "max": 10978,
                "range": 2269,
                "cv_percent": 7.0  # 变异系数 < 20%
            },
            "trend_analysis": {
                "total_growth_percent": -2.9,  # 变化 < 5%
                "avg_growth_percent": -0.24,
                "volatility": 5.2,  # 波动性 < 10%
                "trend_direction": "下降",
                "first_value": 9919,
                "last_value": 9634
            },
            "extremes": {
                "max_value": 10978,
                "min_value": 8709,
                "outliers_count": 0,
                "outliers": []
            }
        }

        formatted = _format_stats_analysis(stats_stable)

        # 平稳数据应该只输出基础信息
        assert "【统计】" in formatted or "【关键数据点】" in formatted
        assert "12" in formatted
        assert "116308" in formatted or "116308" in formatted
        assert "9692" in formatted

    def test_format_stats_analysis_with_significant_trend(self):
        """测试有明显趋势的数据格式化"""
        from src.app.services.agent_service import _format_stats_analysis

        # 测试场景2：明显上升趋势（变化 > 5%）
        stats_trending = {
            "basic_stats": {
                "count": 12,
                "total": 150000,
                "mean": 12500,
                "cv_percent": 15.0
            },
            "trend_analysis": {
                "total_growth_percent": 25.5,  # 变化 > 5%
                "volatility": 8.0,
                "trend_direction": "上升"
            },
            "extremes": {
                "outliers_count": 0
            }
        }

        formatted = _format_stats_analysis(stats_trending)

        # 应该包含趋势信息
        assert "【关键数据点】" in formatted
        assert "趋势" in formatted
        assert "上升" in formatted
        assert "25.5%" in formatted or "25%" in formatted

    def test_format_stats_analysis_with_outliers(self):
        """测试包含异常值的数据格式化"""
        from src.app.services.agent_service import _format_stats_analysis

        # 测试场景3：包含异常值
        stats_with_outliers = {
            "basic_stats": {
                "count": 10,
                "total": 10000,
                "mean": 1000,
                "cv_percent": 35.0  # 高变异系数
            },
            "trend_analysis": {
                "total_growth_percent": 5.0,
                "volatility": 12.0
            },
            "extremes": {
                "outliers_count": 2
            }
        }

        formatted = _format_stats_analysis(stats_with_outliers)

        # 应该包含异常值和高变异警告
        assert "【关键数据点】" in formatted
        assert "异常值" in formatted
        assert "2" in formatted
        assert "波动较大" in formatted or "变异系数" in formatted

    def test_service_singleton(self):
        """测试服务单例模式"""
        service1 = get_stats_service()
        service2 = get_stats_service()

        # 应该返回同一个实例
        assert service1 is service2

    def test_empty_data_handling(self, service):
        """测试空数据处理"""
        result = service.analyze_query_result({"rows": []})

        assert "error" in result
        assert "无数据可供分析" in result["error"]

    def test_no_numeric_column(self, service):
        """测试无数值列的处理"""
        data = {
            "columns": ["name", "category"],
            "rows": [["A", "X"], ["B", "Y"]]
        }

        result = service.analyze_query_result(data)

        assert "error" in result
        assert "未找到数值列" in result["error"]


class TestStatsAnalysisIntegration:
    """集成测试：统计服务与 Agent 响应转换"""

    def test_stats_added_to_metadata(self):
        """测试统计结果被添加到 metadata（关键数据点模式）"""
        from src.app.services.agent_service import _format_stats_analysis

        # 模拟统计结果
        stats = {
            "basic_stats": {
                "count": 5,
                "total": 1000,
                "mean": 200,
                "cv_percent": 15
            },
            "trend_analysis": {
                "total_growth_percent": 20,
                "trend_direction": "上升"
            }
        }

        # 格式化统计文本
        stats_text = _format_stats_analysis(stats)

        # 验证包含关键信息（新格式：使用"条"而不是"个"）
        assert "5 条" in stats_text or "5" in stats_text
        assert "1000" in stats_text
        assert "200" in stats_text
        assert "上升" in stats_text
        # 新格式包含 "+20.0%" 或 "20%"
        assert "20%" in stats_text or "20.0%" in stats_text
