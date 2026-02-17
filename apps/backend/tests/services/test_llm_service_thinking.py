"""
测试智谱AI思考模式自动启用功能

验证所有数据查询类问题都能启用思考模式，确保深入分析
"""

import pytest
from src.app.services.llm_service import ZhipuProvider, LLMMessage


class TestThinkingMode:
    """测试思考模式自动启用"""

    @pytest.fixture
    def provider(self):
        """创建 ZhipuProvider 测试实例"""
        return ZhipuProvider(api_key="test_key", tenant_id="test_tenant")

    @pytest.mark.parametrize("query,expected", [
        # 数据查询关键词测试
        ("显示所有客户", True),
        ("销售额是多少", True),
        ("最近的订单", True),
        ("数据列表", True),
        ("查询销售数据", True),
        ("统计订单数量", True),
        ("本月收入", True),
        ("昨天新增客户", True),
        # 思考指示词测试（原有逻辑）
        ("分析销售趋势", True),
        ("比较两个产品", True),
        ("评估业绩", True),
        ("解释数据", True),
        # 简单查询（应该默认启用）
        ("订单列表", True),
        ("客户数据", True),
    ])
    def test_thinking_mode_always_enabled_for_data_queries(self, provider, query, expected):
        """所有数据查询类问题都应该启用思考模式"""
        messages = [LLMMessage(role="user", content=query)]
        result = provider.should_enable_thinking(messages)
        assert result == expected, (
            f"查询: '{query}'\n"
            f"预期: {expected} (启用思考模式)\n"
            f"实际: {result}"
        )

    def test_thinking_mode_with_complex_query(self, provider):
        """复杂查询应启用思考模式"""
        query = "请帮我分析一下最近一个月的销售趋势，并对比去年同期数据，" \
                "找出增长最快的产品类别，并给出可能的原因分析"
        messages = [LLMMessage(role="user", content=query)]
        result = provider.should_enable_thinking(messages)
        assert result is True, "复杂查询应启用思考模式"

    def test_thinking_mode_with_multiple_questions(self, provider):
        """多个问号的问题应启用思考模式"""
        query = "销售额是多少？利润怎么样？哪个产品卖得最好？"
        messages = [LLMMessage(role="user", content=query)]
        result = provider.should_enable_thinking(messages)
        assert result is True, "多个问号的问题应启用思考模式"

    def test_thinking_mode_with_long_query(self, provider):
        """长问题应启用思考模式"""
        query = "请帮我分析一下最近一个月的客户数据，" + "详细说明" * 50
        messages = [LLMMessage(role="user", content=query)]
        result = provider.should_enable_thinking(messages)
        assert result is True, "长问题应启用思考模式"

    def test_thinking_mode_default_behavior(self, provider):
        """即使不包含关键词，也应该默认启用思考模式"""
        # 这个测试验证默认行为 - 任何问题都应该启用思考模式
        query = "你好"  # 不包含任何特定关键词
        messages = [LLMMessage(role="user", content=query)]
        result = provider.should_enable_thinking(messages)
        # 根据新逻辑，默认应该返回 True
        assert result is True, "默认应该启用思考模式"

    def test_thinking_mode_with_empty_content(self, provider):
        """空内容应返回 False"""
        messages = [LLMMessage(role="user", content="")]
        result = provider.should_enable_thinking(messages)
        assert result is False, "空内容应返回 False"

    def test_thinking_mode_exception_handling(self, provider):
        """测试异常处理 - 出错时应默认启用"""
        # 传入无效消息格式，触发异常处理
        messages = []  # 空列表
        result = provider.should_enable_thinking(messages)
        # 异常情况下应默认返回 True
        assert result is True, "异常情况应默认启用思考模式"
