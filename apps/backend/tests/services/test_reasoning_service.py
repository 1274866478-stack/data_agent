"""
推理服务测试
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.app.services.reasoning_service import (
    reasoning_engine,
    QueryUnderstandingEngine,
    AnswerGenerator,
    QueryType,
    ReasoningMode,
    QueryAnalysis,
    ReasoningResult,
    ReasoningStep
)


class TestQueryUnderstandingEngine:
    """查询理解引擎测试"""

    @pytest.fixture
    def engine(self):
        return QueryUnderstandingEngine()

    @pytest.mark.asyncio
    async def test_analyze_factual_query(self, engine):
        """测试事实查询分析"""
        query = "什么是人工智能？"

        analysis = await engine.analyze_query(query)

        assert analysis.original_query == query
        assert analysis.query_type in [QueryType.FACTUAL, QueryType.UNKNOWN]
        assert analysis.complexity_score >= 0.0
        assert analysis.complexity_score <= 1.0
        assert analysis.confidence >= 0.0
        assert analysis.confidence <= 1.0
        assert isinstance(analysis.entities, list)
        assert isinstance(analysis.keywords, list)
        assert isinstance(analysis.temporal_expressions, list)

    @pytest.mark.asyncio
    async def test_analyze_comparative_query(self, engine):
        """测试比较查询分析"""
        query = "比较Python和Java的优缺点"

        analysis = await engine.analyze_query(query)

        assert analysis.original_query == query
        assert analysis.query_type == QueryType.COMPARATIVE
        assert "比较" in analysis.intent

    @pytest.mark.asyncio
    async def test_analyze_temporal_query(self, engine):
        """测试时间相关查询分析"""
        query = "2024年的销售趋势如何？"

        analysis = await engine.analyze_query(query)

        assert analysis.original_query == query
        assert analysis.query_type == QueryType.TEMPORAL
        assert len(analysis.temporal_expressions) > 0
        assert "2024" in str(analysis.temporal_expressions)

    @pytest.mark.asyncio
    async def test_extract_entities(self, engine):
        """测试实体提取"""
        query = "分析2024年销售额达到100万元的原因"

        entities = engine._extract_entities(query)

        assert any("2024" in entity for entity in entities)
        assert any("100" in entity for entity in entities)

    @pytest.mark.asyncio
    async def test_calculate_complexity(self, engine):
        """测试复杂度计算"""
        simple_query = "什么是AI？"
        complex_query = "请深入分析比较Python和Java在不同应用场景下的性能表现、开发效率、生态系统支持以及未来发展趋势，并提供具体的技术实现建议"

        simple_complexity = engine._calculate_complexity(simple_query, [], [])
        complex_complexity = engine._calculate_complexity(complex_query, [], [])

        assert complex_complexity > simple_complexity

    @pytest.mark.asyncio
    async def test_suggest_reasoning_mode(self, engine):
        """测试推理模式建议"""
        factual_analysis = QueryAnalysis(
            original_query="简单问题",
            query_type=QueryType.FACTUAL,
            intent="寻求信息",
            entities=[],
            keywords=[],
            temporal_expressions=[],
            complexity_score=0.3,
            confidence=0.8,
            reasoning_mode=ReasoningMode.BASIC,
            suggested_temperature=0.5,
            suggested_max_tokens=1000
        )

        analytical_analysis = QueryAnalysis(
            original_query="复杂问题",
            query_type=QueryType.ANALYTICAL,
            intent="寻求分析",
            entities=[],
            keywords=[],
            temporal_expressions=[],
            complexity_score=0.8,
            confidence=0.9,
            reasoning_mode=ReasoningMode.BASIC,
            suggested_temperature=0.7,
            suggested_max_tokens=2000
        )

        factual_mode = engine._suggest_reasoning_mode(factual_analysis.query_type, factual_analysis.complexity_score)
        analytical_mode = engine._suggest_reasoning_mode(analytical_analysis.query_type, analytical_analysis.complexity_score)

        assert factual_mode == ReasoningMode.BASIC
        assert analytical_mode in [ReasoningMode.ANALYTICAL, ReasoningMode.STEP_BY_STEP]


class TestAnswerGenerator:
    """答案生成器测试"""

    @pytest.fixture
    def generator(self):
        return AnswerGenerator()

    @pytest.fixture
    def sample_query_analysis(self):
        return QueryAnalysis(
            original_query="什么是机器学习？",
            query_type=QueryType.FACTUAL,
            intent="寻求定义",
            entities=["机器学习"],
            keywords=["机器学习", "定义"],
            temporal_expressions=[],
            complexity_score=0.4,
            confidence=0.8,
            reasoning_mode=ReasoningMode.BASIC,
            suggested_temperature=0.5,
            suggested_max_tokens=1000
        )

    @pytest.mark.asyncio
    async def test_generate_reasoning_steps(self, generator, sample_query_analysis):
        """测试推理步骤生成"""
        steps = await generator._generate_reasoning_steps(sample_query_analysis, None, None)

        assert len(steps) >= 1
        assert all(isinstance(step, ReasoningStep) for step in steps)
        assert steps[0].step_number == 1
        assert steps[0].description is not None
        assert steps[0].reasoning is not None
        assert 0 <= steps[0].confidence <= 1

    @pytest.mark.asyncio
    @patch('src.app.services.reasoning_service.llm_service')
    async def test_generate_main_answer_with_llm_service(self, mock_llm_service, generator, sample_query_analysis):
        """测试使用LLM服务生成主要答案"""
        # Mock LLM服务响应
        mock_response = Mock()
        mock_response.content = "机器学习是人工智能的一个分支..."
        mock_llm_service.chat_completion = AsyncMock(return_value=mock_response)

        reasoning_steps = await generator._generate_reasoning_steps(sample_query_analysis, None, None)
        answer = await generator._generate_main_answer(sample_query_analysis, reasoning_steps, None, "test_tenant")

        assert answer == "机器学习是人工智能的一个分支..."
        mock_llm_service.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.app.services.reasoning_service.zhipu_service')
    async def test_generate_main_answer_fallback_to_zhipu(self, mock_zhipu_service, generator, sample_query_analysis):
        """测试LLM服务失败时回退到智谱服务"""
        # Mock LLM服务失败，智谱服务成功
        mock_llm_response = None
        mock_zhipu_response = {"content": "机器学习是让计算机模拟人类学习过程的技术"}

        with patch('src.app.services.reasoning_service.llm_service') as mock_llm_service:
            mock_llm_service.chat_completion = AsyncMock(return_value=mock_llm_response)
            mock_zhipu_service.chat_completion = AsyncMock(return_value=mock_zhipu_response)

            reasoning_steps = await generator._generate_reasoning_steps(sample_query_analysis, None, None)
            answer = await generator._generate_main_answer(sample_query_analysis, reasoning_steps, None, "test_tenant")

            assert answer == "机器学习是让计算机模拟人类学习过程的技术"

    def test_calculate_confidence(self, generator):
        """测试置信度计算"""
        steps = [
            ReasoningStep(1, "测试步骤1", "测试推理", [], 0.8),
            ReasoningStep(2, "测试步骤2", "测试推理", [], 0.6)
        ]
        answer = "这是一个完整的答案，包含足够的信息来回答用户的问题。"

        confidence = generator._calculate_confidence(steps, answer)

        assert 0 <= confidence <= 1
        assert confidence > 0.5  # 基于步骤置信度和答案长度应该有较高置信度

    def test_calculate_quality_score(self, generator):
        """测试质量分数计算"""
        steps = [
            ReasoningStep(1, "分析问题", "首先分析用户问题的核心需求", [], 0.9),
            ReasoningStep(2, "提供答案", "基于分析结果提供准确答案", [], 0.8),
            ReasoningStep(3, "总结建议", "最后给出实用的建议", [], 0.7)
        ]
        high_quality_answer = "首先，需要明确问题的核心。其次，分析相关的技术方案。最后，提供具体的实施建议。"
        low_quality_answer = "简短回答"

        high_score = generator._calculate_quality_score(high_quality_answer, steps)
        low_score = generator._calculate_quality_score(low_quality_answer, [])

        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1
        assert high_score > low_score

    @pytest.mark.asyncio
    async def test_safety_filter(self, generator):
        """测试安全过滤"""
        safe_content = "这是一个安全的回答"
        unsafe_content = "这个回答包含暴力内容"

        safe_triggered = await generator._safety_filter(safe_content)
        unsafe_triggered = await generator._safety_filter(unsafe_content)

        assert safe_triggered == False
        assert unsafe_triggered == True

    def test_prepare_sources(self, generator):
        """测试源信息准备"""
        data_sources = [
            {"id": "source1", "name": "技术文档", "type": "document", "relevance": 0.9},
            {"id": "source2", "name": "研究报告", "type": "report", "relevance": 0.7},
            {"id": "source3", "name": "新闻文章", "type": "article", "relevance": 0.5}
        ]

        sources = generator._prepare_sources(data_sources)

        assert len(sources) == 3
        assert all("id" in source for source in sources)
        assert all("name" in source for source in sources)
        assert all("type" in source for source in sources)
        assert all("relevance" in source for source in sources)


class TestReasoningEngine:
    """推理引擎测试"""

    @pytest.fixture
    def engine(self):
        return ReasoningEngine()

    @pytest.mark.asyncio
    @patch('src.app.services.reasoning_service.AnswerGenerator.generate_answer')
    async def test_reason_simple_query(self, mock_generate_answer, engine):
        """测试简单查询推理"""
        # Mock答案生成
        mock_result = ReasoningResult(
            answer="机器学习是人工智能的一个重要分支。",
            reasoning_steps=[
                ReasoningStep(1, "理解查询", "识别用户想了解机器学习的定义", [], 0.9)
            ],
            confidence=0.85,
            sources=[],
            query_analysis=QueryAnalysis(
                original_query="什么是机器学习？",
                query_type=QueryType.FACTUAL,
                intent="寻求定义",
                entities=["机器学习"],
                keywords=["机器学习"],
                temporal_expressions=[],
                complexity_score=0.3,
                confidence=0.9,
                reasoning_mode=ReasoningMode.BASIC,
                suggested_temperature=0.3,
                suggested_max_tokens=1000
            ),
            quality_score=0.8,
            safety_filter_triggered=False
        )
        mock_generate_answer.return_value = mock_result

        result = await engine.reason(
            query="什么是机器学习？",
            tenant_id="test_tenant"
        )

        assert result.answer == "机器学习是人工智能的一个重要分支。"
        assert result.confidence == 0.85
        assert result.query_analysis.original_query == "什么是机器学习？"
        assert result.safety_filter_triggered == False
        assert "processing_time" in result.metadata

    @pytest.mark.asyncio
    async def test_reason_with_context(self, engine):
        """测试带上下文的推理"""
        context = [
            {"role": "user", "content": "我对编程很感兴趣"},
            {"role": "assistant", "content": "编程是一项很好的技能"}
        ]

        with patch.object(engine.answer_generator, 'generate_answer') as mock_generate:
            mock_generate.return_value = ReasoningResult(
                answer="基于您的编程兴趣，我建议...",
                reasoning_steps=[],
                confidence=0.8,
                sources=[],
                query_analysis=QueryAnalysis(
                    original_query="学习什么编程语言？",
                    query_type=QueryType.PROCEDURAL,
                    intent="寻求建议",
                    entities=[],
                    keywords=["编程语言"],
                    temporal_expressions=[],
                    complexity_score=0.5,
                    confidence=0.8,
                    reasoning_mode=ReasoningMode.CONTEXT_AWARE,
                    suggested_temperature=0.6,
                    suggested_max_tokens=1500
                ),
                quality_score=0.75,
                safety_filter_triggered=False
            )

            result = await engine.reason(
                query="学习什么编程语言？",
                context=context,
                tenant_id="test_tenant"
            )

            mock_generate.assert_called_once()
            # 验证上下文被传递给答案生成器
            call_args = mock_generate.call_args
            assert call_args[1]['context'] == context

    @pytest.mark.asyncio
    async def test_reason_with_specific_mode(self, engine):
        """测试指定推理模式"""
        with patch.object(engine.answer_generator, 'generate_answer') as mock_generate:
            mock_result = ReasoningResult(
                answer="按步骤分析...",
                reasoning_steps=[
                    ReasoningStep(1, "第一步", "分析需求", [], 0.9),
                    ReasoningStep(2, "第二步", "评估选项", [], 0.8)
                ],
                confidence=0.85,
                sources=[],
                query_analysis=QueryAnalysis(
                    original_query="如何选择技术栈？",
                    query_type=QueryType.PROCEDURAL,
                    intent="寻求步骤",
                    entities=[],
                    keywords=["技术栈", "选择"],
                    temporal_expressions=[],
                    complexity_score=0.6,
                    confidence=0.8,
                    reasoning_mode=ReasoningMode.STEP_BY_STEP,
                    suggested_temperature=0.5,
                    suggested_max_tokens=2000
                ),
                quality_score=0.8,
                safety_filter_triggered=False
            )
            mock_generate.return_value = mock_result

            result = await engine.reason(
                query="如何选择技术栈？",
                reasoning_mode=ReasoningMode.STEP_BY_STEP,
                tenant_id="test_tenant"
            )

            assert result.query_analysis.reasoning_mode == ReasoningMode.STEP_BY_STEP

    @pytest.mark.asyncio
    async def test_reason_error_handling(self, engine):
        """测试推理错误处理"""
        with patch.object(engine.answer_generator, 'generate_answer') as mock_generate:
            mock_generate.side_effect = Exception("模拟错误")

            result = await engine.reason(
                query="测试查询",
                tenant_id="test_tenant"
            )

            # 应该返回默认的错误处理结果
            assert result.answer == "抱歉，处理您的查询时遇到了问题，请稍后重试。"
            assert result.confidence == 0.1
            assert result.quality_score == 0.1
            assert result.safety_filter_triggered == True
            assert "error" in result.metadata


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_reasoning(self):
        """端到端推理测试"""
        # 这个测试需要实际的LLM服务，在CI/CD环境中应该被mock
        engine = ReasoningEngine()

        with patch.object(engine.answer_generator, '_generate_main_answer') as mock_main_answer:
            mock_main_answer.return_value = "机器学习是人工智能的一个核心分支，它使计算机能够从数据中学习并改进性能。"

            result = await engine.reason(
                query="请解释什么是机器学习及其主要应用领域",
                tenant_id="integration_test"
            )

            assert result.answer is not None
            assert len(result.reasoning_steps) >= 1
            assert 0 <= result.confidence <= 1
            assert 0 <= result.quality_score <= 1
            assert result.query_analysis.original_query == "请解释什么是机器学习及其主要应用领域"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])