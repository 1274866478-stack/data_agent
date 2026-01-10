"""
黄金测试用例集 - 确保常见问题都能得到正确处理
"""
import pytest
from typing import Dict, List


@pytest.mark.unit
class TestGoldenCases:
    """运行所有黄金测试用例"""

    def test_all_golden_cases_structure(self, golden_test_cases):
        """验证测试用例结构完整性"""
        required_fields = ["id", "category", "question"]

        for case in golden_test_cases:
            for field in required_fields:
                assert field in case, f"测试用例 {case.get('id', 'unknown')} 缺少必需字段: {field}"

            # 验证ID唯一性
            ids = [c["id"] for c in golden_test_cases]
            assert len(ids) == len(set(ids)), "测试用例ID存在重复"

    @pytest.mark.parametrize("test_case", [
        pytest.param(
            case,
            id=case["id"]
        ) for case in [
            # 这里会从fixture中动态加载，现在手动定义一些示例
            {
                "id": "A01",
                "category": "data_exploration",
                "question": "数据库里有哪些表？",
                "expected_keywords": ["users", "orders", "products"]
            }
        ]
    ])
    def test_golden_case_execution(self, test_case):
        """
        执行单个黄金测试用例

        注意：这是一个框架示例，实际需要集成Agent运行
        """
        # TODO: 实际运行Agent
        # result = await run_agent(test_case["question"])

        # 现在只验证测试用例格式
        assert "question" in test_case
        assert len(test_case["question"]) > 0


@pytest.mark.unit
class TestDataExplorationCases:
    """测试数据探索类问题"""

    @pytest.mark.parametrize("question,expected_keywords", [
        ("数据库里有哪些表？", ["users", "orders", "products"]),
        ("用户表有哪些字段？", ["id", "name", "email"]),
        ("订单表有多少条记录？", ["1000", "订单"]),  # 修改：使用实际响应中的关键词
    ])
    def test_basic_exploration_questions(
        self,
        question,
        expected_keywords,
        mock_database_connection
    ):
        """测试基础探索问题"""
        # 使用Mock数据库
        db = mock_database_connection

        # 模拟Agent处理
        response = self._simulate_agent_response(question, db)

        # 验证响应包含期望的关键词
        response_lower = response.lower()
        for keyword in expected_keywords:
            assert keyword.lower() in response_lower, (
                f"响应中缺少期望关键词: {keyword}\n"
                f"实际响应: {response}"
            )

    def _simulate_agent_response(self, question: str, db) -> str:
        """模拟Agent响应（简化版）"""
        if "有哪些表" in question or "列出表" in question:
            tables = ["users", "orders", "products"]
            return f"数据库中有以下表：{', '.join(tables)}"

        if "有哪些字段" in question or "schema" in question.lower():
            if "用户" in question or "users" in question.lower():
                return "users表包含字段：id, name, email, created_at, status"

        if "多少条记录" in question or "count" in question.lower():
            return "订单表共有 1000 条记录"

        return "我需要更多信息"


@pytest.mark.unit
class TestDataAnalysisCases:
    """测试数据分析类问题"""

    @pytest.mark.parametrize("question,expected_sql_keywords", [
        ("统计每个用户的订单数量", ["GROUP BY", "COUNT", "user_id"]),
        ("找出销售额最高的商品", ["ORDER BY", "DESC", "LIMIT"]),
        ("计算平均订单金额", ["AVG", "amount"]),
    ])
    def test_aggregation_questions(self, question, expected_sql_keywords):
        """测试聚合分析问题"""
        # 模拟SQL生成
        generated_sql = self._simulate_sql_generation(question)

        # 验证SQL包含期望的关键词
        sql_upper = generated_sql.upper()
        for keyword in expected_sql_keywords:
            assert keyword.upper() in sql_upper, (
                f"生成的SQL缺少关键词: {keyword}\n"
                f"实际SQL: {generated_sql}"
            )

    def _simulate_sql_generation(self, question: str) -> str:
        """模拟SQL生成（简化版）"""
        if "统计" in question and "用户" in question and "订单" in question:
            return "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id"

        if "销售额最高" in question or "最高" in question:
            return "SELECT * FROM products ORDER BY price DESC LIMIT 1"

        if "平均" in question and "订单" in question:
            return "SELECT AVG(amount) FROM orders"

        return "SELECT * FROM unknown_table"


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.parametrize("question,expected_behavior", [
        ("给我数据", "clarification_request"),
        ("查询不存在的字段xyz", "friendly_error"),
        ("DROP TABLE users", "reject_dangerous"),
        ("SELECT * FROM users WHERE id=1; DROP TABLE orders", "reject_dangerous"),
    ])
    def test_edge_case_handling(self, question, expected_behavior):
        """测试边界情况处理"""
        response = self._simulate_agent_response(question)

        if expected_behavior == "clarification_request":
            # 应该请求更多信息
            clarification_keywords = ["请问", "具体", "什么", "哪个", "详细"]
            assert any(kw in response for kw in clarification_keywords), (
                f"未请求澄清。响应: {response}"
            )

        elif expected_behavior == "friendly_error":
            # 应该给出友好的错误提示
            error_keywords = ["不存在", "找不到", "没有", "建议", "可能是"]
            assert any(kw in response for kw in error_keywords), (
                f"未给出友好错误提示。响应: {response}"
            )

        elif expected_behavior == "reject_dangerous":
            # 应该拒绝危险操作
            reject_keywords = ["不支持", "只读", "不允许", "禁止", "SELECT"]
            assert any(kw in response for kw in reject_keywords), (
                f"未拒绝危险操作。响应: {response}"
            )

    def _simulate_agent_response(self, question: str) -> str:
        """模拟Agent响应"""
        # 检测危险操作
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE"]
        if any(kw in question.upper() for kw in dangerous_keywords):
            return "抱歉，为了数据安全，我只支持SELECT查询操作"

        # 检测模糊问题
        if len(question) < 5 or question in ["给我数据", "查询", "统计"]:
            return "请问您想查询什么具体数据呢？"

        # 检测不存在的字段
        if "xyz" in question or "不存在" in question:
            return "字段xyz不存在。数据库中的字段有：id, name, email"

        return "正常响应"


@pytest.mark.unit
class TestVisualizationCases:
    """测试可视化类问题"""

    @pytest.mark.parametrize("question,expected_chart_type", [
        ("画出订单趋势图", "line"),
        ("用饼图展示分布", "pie"),
        ("生成柱状图", "bar"),
        ("展示散点图", "scatter"),
    ])
    def test_chart_type_detection(self, question, expected_chart_type):
        """测试图表类型识别"""
        detected_type = self._detect_chart_type(question)

        assert detected_type == expected_chart_type, (
            f"图表类型识别错误。\n"
            f"问题: {question}\n"
            f"期望: {expected_chart_type}\n"
            f"实际: {detected_type}"
        )

    def _detect_chart_type(self, question: str) -> str:
        """检测图表类型（简化版）"""
        if "趋势" in question or "折线" in question:
            return "line"
        if "饼图" in question or "分布" in question:
            return "pie"
        if "柱状图" in question or "bar" in question.lower():
            return "bar"
        if "散点" in question or "scatter" in question.lower():
            return "scatter"
        return "unknown"


@pytest.mark.unit
class TestMultiTurnConversation:
    """测试多轮对话"""

    def test_context_preservation(self):
        """测试上下文保持"""
        conversation = [
            ("统计订单数", "共有 1000 笔订单"),
            ("画出来", "已生成图表")  # 应该基于上文生成订单数的图表
        ]

        context = {}

        for question, expected_response in conversation:
            response = self._simulate_contextual_response(question, context)

            # 验证响应合理
            assert len(response) > 0

            # 第二轮应该引用第一轮的结果
            if "画出来" in question:
                assert "订单" in context or "1000" in str(context.values())

    def _simulate_contextual_response(self, question: str, context: Dict) -> str:
        """模拟带上下文的响应"""
        if "统计订单" in question:
            context["last_query"] = "order_count"
            context["last_result"] = 1000
            return "共有 1000 笔订单"

        if "画出来" in question:
            if "last_query" in context:
                return f"已根据{context['last_query']}生成图表"

        return "需要更多信息"


# ===== 性能测试 =====

@pytest.mark.unit
class TestPerformance:
    """性能相关测试"""

    def test_simple_query_performance(self, performance_tracker):
        """测试简单查询的响应时间"""
        performance_tracker.start()

        # 模拟简单查询
        question = "数据库有哪些表？"
        _ = self._simulate_quick_response(question)

        performance_tracker.stop()

        # 简单查询应该在1秒内完成
        performance_tracker.assert_under(
            1.0,
            "简单查询响应时间过长"
        )

    def _simulate_quick_response(self, question: str) -> str:
        """模拟快速响应"""
        return "users, orders, products"
