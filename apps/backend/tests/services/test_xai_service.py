"""
XAI服务测试
测试可解释性AI功能，包括解释生成、源数据追踪、不确定性量化等
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import json

from src.app.services.xai_service import (
    xai_service,
    XAIService,
    ExplanationType,
    VisualizationType,
    ExplanationStep,
    SourceTrace,
    UncertaintyQuantification,
    AlternativeAnswer,
    XAIExplanation
)


class TestXAIService:
    """XAI服务测试类"""

    @pytest.fixture
    def sample_sources(self) -> List[Dict[str, Any]]:
        """示例数据源"""
        return [
            {
                "source_id": "sql_001",
                "source_type": "sql_query",
                "name": "销售数据库",
                "content": "产品A在第三季度的销售额为120万元",
                "confidence": 0.95,
                "relevance_score": 0.9,
                "metadata": {
                    "query": "SELECT sales FROM products WHERE quarter='Q3'",
                    "table": "sales_data"
                }
            },
            {
                "source_id": "rag_001",
                "source_type": "rag_retrieval",
                "name": "市场分析报告",
                "content": "根据市场分析，第三季度表现超出预期，主要得益于产品A的强劲销售",
                "confidence": 0.88,
                "relevance_score": 0.85,
                "metadata": {
                    "collection": "market_reports",
                    "similarity_score": 0.92
                }
            }
        ]

    @pytest.fixture
    def sample_fusion_result(self) -> Dict[str, Any]:
        """示例融合结果"""
        return {
            "answer": "根据数据分析，第三季度销售额达到120万元，表现超出预期",
            "confidence": 0.85,
            "answer_quality_score": 0.82,
            "sources": [
                {"source_id": "sql_001", "confidence": 0.95},
                {"source_id": "rag_001", "confidence": 0.88}
            ],
            "conflicts": [],
            "processing_time": 2.5
        }

    @pytest.fixture
    def sample_reasoning_steps(self) -> List[Dict[str, Any]]:
        """示例推理步骤"""
        return [
            {
                "step_number": 1,
                "description": "理解查询意图",
                "confidence": 0.9,
                "evidence": ["识别到时间范围：第三季度", "识别到关键主题：销售表现"]
            },
            {
                "step_number": 2,
                "description": "数据收集与分析",
                "confidence": 0.85,
                "evidence": ["从数据库检索销售数据", "分析市场报告内容"]
            }
        ]

    @pytest.mark.asyncio
    async def test_generate_explanation_basic(
        self,
        sample_sources,
        sample_fusion_result,
        sample_reasoning_steps
    ):
        """测试基本解释生成"""
        query = "第三季度的销售表现如何？"
        answer = "第三季度销售表现良好，销售额达到120万元，超出预期目标。"

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            fusion_result=sample_fusion_result,
            reasoning_steps=sample_reasoning_steps,
            sources=sample_sources,
            tenant_id="test_tenant"
        )

        assert isinstance(result, XAIExplanation)
        assert result.query == query
        assert result.answer == answer
        assert len(result.explanation_steps) > 0
        assert len(result.source_traces) > 0
        assert result.confidence_explanation is not None
        assert result.uncertainty_quantification is not None
        assert result.explanation_quality_score >= 0

    @pytest.mark.asyncio
    async def test_explanation_without_fusion_result(self, sample_sources):
        """测试没有融合结果时的解释生成"""
        query = "简单测试查询"
        answer = "这是一个简单答案"

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            sources=sample_sources,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.query == query
        assert result.answer == answer
        # 即使没有融合结果，也应该生成基础解释
        assert len(result.explanation_steps) > 0

    @pytest.mark.asyncio
    async def test_explanation_with_minimal_input(self):
        """测试最小输入的解释生成"""
        query = "测试"
        answer = "答案"

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.query == query
        assert result.answer == answer
        # 即使只有基础输入，也应该生成解释
        assert len(result.explanation_steps) > 0
        assert result.explanation_quality_score > 0

    @pytest.mark.asyncio
    async def test_explanation_steps_generation(self):
        """测试解释步骤生成"""
        query = "分析第三季度销售数据并预测第四季度趋势"
        answer = "基于第三季度的强劲表现，预计第四季度将保持增长趋势。"

        service = XAIService()
        steps = await service._generate_explanation_steps(
            query=query,
            answer=answer,
            fusion_result=None,
            reasoning_steps=None,
            sources=[]
        )

        assert len(steps) > 0

        # 检查必要步骤
        step_titles = [step.title for step in steps]
        assert any("查询理解" in title for title in step_titles)
        assert any("答案生成" in title for title in step_titles)

        # 检查步骤属性
        for step in steps:
            assert step.step_number > 0
            assert step.title is not None
            assert step.description is not None
            assert 0 <= step.confidence <= 1

    @pytest.mark.asyncio
    async def test_query_understanding_explanation(self):
        """测试查询理解解释"""
        service = XAIService()
        query = "比较分析第三季度和第二季度的销售数据，找出增长原因"

        step = await service._explain_query_understanding(query, 1)

        assert step.explanation_type == ExplanationType.REASONING_PROCESS
        assert step.title == "查询理解"
        assert len(step.evidence) > 0
        assert step.confidence > 0
        assert "比较" in " ".join(step.evidence) or "分析" in " ".join(step.evidence)

    @pytest.mark.asyncio
    async def test_data_source_selection_explanation(self, sample_sources):
        """测试数据源选择解释"""
        service = XAIService()

        step = await service._explain_data_source_selection(sample_sources, 2)

        assert step.explanation_type == ExplanationType.DATA_SOURCE
        assert step.title == "数据源选择"
        assert len(step.evidence) > 0
        assert f"{len(sample_sources)}个数据源" in step.description

    @pytest.mark.asyncio
    async def test_source_trace_building(self, sample_sources):
        """测试源数据追踪构建"""
        answer = "根据销售数据和市场分析，第三季度表现良好。"

        traces = await xai_service._build_source_traces(sample_sources, answer)

        assert len(traces) == len(sample_sources)

        for trace in traces:
            assert trace.source_id is not None
            assert trace.source_type is not None
            assert trace.source_name is not None
            assert trace.content_snippet is not None
            assert 0 <= trace.relevance_score <= 1
            assert 0 <= trace.confidence_contribution <= 1
            assert trace.verification_status is not None

    @pytest.mark.asyncio
    async def test_decision_tree_building(self):
        """测试决策树构建"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="查询理解",
                description="理解用户查询",
                confidence=0.9
            ),
            ExplanationStep(
                step_number=2,
                explanation_type=ExplanationType.DATA_SOURCE,
                title="数据收集",
                description="收集相关数据",
                confidence=0.85
            )
        ]

        tree = await xai_service._build_decision_tree(explanation_steps, [])

        assert len(tree) > 0
        assert "root" in tree
        assert tree["root"].node_type == "decision"
        assert tree["root"].title == "查询理解"

    @pytest.mark.asyncio
    async def test_uncertainty_quantification(self, sample_sources):
        """测试不确定性量化"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="测试步骤",
                description="测试描述",
                confidence=0.7
            )
        ]

        fusion_result = {
            "confidence": 0.8,
            "answer_quality_score": 0.75
        }

        uncertainty = await xai_service._quantify_uncertainty(
            explanation_steps=explanation_steps,
            fusion_result=fusion_result,
            sources=sample_sources
        )

        assert isinstance(uncertainty, UncertaintyQuantification)
        assert 0 <= uncertainty.total_uncertainty <= 1
        assert 0 <= uncertainty.data_uncertainty <= 1
        assert 0 <= uncertainty.model_uncertainty <= 1
        assert 0 <= uncertainty.reasoning_uncertainty <= 1
        assert len(uncertainty.uncertainty_sources) >= 0
        assert len(uncertainty.mitigation_suggestions) >= 0

    @pytest.mark.asyncio
    async def test_alternative_answer_generation(self, sample_sources):
        """测试替代答案生成"""
        query = "分析第三季度销售表现"
        primary_answer = "第三季度销售表现良好，销售额达到120万元。"

        alternatives = await xai_service._generate_alternative_answers(
            query=query,
            primary_answer=primary_answer,
            sources=sample_sources,
            tenant_id="test_tenant"
        )

        assert isinstance(alternatives, list)
        # 替代答案可能是空的，这取决于LLM响应
        for alt in alternatives:
            assert alt.title is not None
            assert alt.content is not None
            assert alt.scenario_description is not None
            assert isinstance(alt.confidence_comparison, dict)

    @pytest.mark.asyncio
    async def test_confidence_explanation(self, sample_sources):
        """测试置信度解释"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="测试步骤",
                description="测试描述",
                confidence=0.8
            )
        ]

        fusion_result = {
            "confidence": 0.85,
            "answer_quality_score": 0.82,
            "sources": sample_sources
        }

        explanation = await xai_service._explain_confidence(
            explanation_steps=explanation_steps,
            fusion_result=fusion_result
        )

        assert "overall_confidence" in explanation
        assert "confidence_level" in explanation
        assert "confidence_description" in explanation
        assert "confidence_factors" in explanation
        assert "improvement_suggestions" in explanation
        assert 0 <= explanation["overall_confidence"] <= 1

    @pytest.mark.asyncio
    async def test_visualization_data_generation(self):
        """测试可视化数据生成"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="测试步骤1",
                description="测试描述1",
                confidence=0.8
            ),
            ExplanationStep(
                step_number=2,
                explanation_type=ExplanationType.DATA_SOURCE,
                title="测试步骤2",
                description="测试描述2",
                confidence=0.75
            )
        ]

        decision_tree = {
            "root": {
                "node_id": "root",
                "node_type": "decision",
                "title": "查询理解",
                "content": "理解查询",
                "confidence": 0.9,
                "children": []
            }
        }

        uncertainty = UncertaintyQuantification(
            total_uncertainty=0.2,
            data_uncertainty=0.1,
            model_uncertainty=0.05,
            reasoning_uncertainty=0.05,
            uncertainty_sources=["limited_data"],
            mitigation_suggestions=["add_more_sources"]
        )

        viz_data = await xai_service._generate_visualization_data(
            explanation_steps=explanation_steps,
            decision_tree=decision_tree,
            uncertainty_quant=uncertainty
        )

        assert "decision_tree" in viz_data
        assert "timeline" in viz_data
        assert "uncertainty_heatmap" in viz_data
        assert "confidence_distribution" in viz_data

        # 检查决策树可视化数据
        assert len(viz_data["decision_tree"]["nodes"]) > 0
        assert len(viz_data["decision_tree"]["edges"]) >= 0

        # 检查时间线数据
        assert len(viz_data["timeline"]) == len(explanation_steps)

        # 检查不确定性热图数据
        assert viz_data["uncertainty_heatmap"]["total_uncertainty"] == 0.2

    @pytest.mark.asyncio
    async def test_explanation_quality_calculation(self):
        """测试解释质量计算"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="测试步骤1",
                description="测试描述1",
                confidence=0.8
            ),
            ExplanationStep(
                step_number=2,
                explanation_type=ExplanationType.DATA_SOURCE,
                title="测试步骤2",
                description="测试描述2",
                confidence=0.85
            ),
            ExplanationStep(
                step_number=3,
                explanation_type=ExplanationType.CONFIDENCE,
                title="测试步骤3",
                description="测试描述3",
                confidence=0.9
            )
        ]

        source_traces = [
            SourceTrace(
                source_id="test_1",
                source_type="sql_query",
                source_name="测试源1",
                content_snippet="测试内容1",
                relevance_score=0.9,
                confidence_contribution=0.85,
                verification_status="verified"
            ),
            SourceTrace(
                source_id="test_2",
                source_type="rag_retrieval",
                source_name="测试源2",
                content_snippet="测试内容2",
                relevance_score=0.8,
                confidence_contribution=0.75,
                verification_status="verified"
            )
        ]

        uncertainty = UncertaintyQuantification(
            total_uncertainty=0.2,
            data_uncertainty=0.1,
            model_uncertainty=0.05,
            reasoning_uncertainty=0.05,
            uncertainty_sources=[],
            mitigation_suggestions=[]
        )

        quality_score = await xai_service._calculate_explanation_quality(
            explanation_steps=explanation_steps,
            source_traces=source_traces,
            uncertainty_quant=uncertainty
        )

        assert 0 <= quality_score <= 1
        # 应该有较高的质量分数，因为有多个步骤和源
        assert quality_score > 0.5

    @pytest.mark.asyncio
    async def test_explanation_types_coverage(self):
        """测试各种解释类型的覆盖"""
        query = "分析销售数据并提供详细解释"
        answer = "销售数据分析完成"

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            tenant_id="test_tenant"
        )

        explanation_types = [step.explanation_type for step in result.explanation_steps]

        # 应该包含基本的解释类型
        expected_types = [
            ExplanationType.REASONING_PROCESS,
            ExplanationType.ASSUMPTION
        ]

        for expected_type in expected_types:
            assert expected_type in explanation_types, f"缺少解释类型: {expected_type}"

    @pytest.mark.asyncio
    async def test_error_handling_in_explanation_generation(self):
        """测试解释生成中的错误处理"""
        # 测试无效输入
        result = await xai_service.generate_explanation(
            query="",  # 空查询
            answer="",  # 空答案
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.query == ""
        assert result.answer == ""
        assert len(result.explanation_steps) >= 0

        # 测试None输入
        result2 = await xai_service.generate_explanation(
            query=None,  # type: ignore
            answer=None,  # type: ignore
            tenant_id="test_tenant"
        )

        assert result2 is not None

    def test_explanation_type_icons(self):
        """测试解释类型图标映射"""
        service = XAIService()

        # 测试所有解释类型都有对应的模板
        for exp_type in ExplanationType:
            template = service.explanation_templates.get(exp_type)
            assert template is not None, f"缺少解释类型模板: {exp_type}"
            assert "{content}" in template, f"模板格式错误: {exp_type}"

    def test_uncertainty_indicators(self):
        """测试不确定性指标"""
        service = XAIService()

        # 验证不确定性指标列表不为空
        assert len(service.uncertainty_indicators) > 0

        # 测试不确定性检测
        content_with_uncertainty = "这可能是因为市场因素导致的，大约增长了15%左右。"
        has_uncertainty = any(indicator in content_with_uncertainty for indicator in service.uncertainty_indicators)
        assert has_uncertainty, "未能检测到不确定性指标"

    @pytest.mark.asyncio
    async def test_explanation_with_complex_query(self):
        """测试复杂查询的解释生成"""
        query = "比较分析我们公司第三季度与竞争对手的表现，考虑市场因素、产品创新和营销策略，并提供改进建议"
        answer = "通过综合分析，公司在第三季度表现优于主要竞争对手，建议继续加强产品创新和营销投入。"

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert len(result.explanation_steps) > 0

        # 复杂查询应该有更多的解释步骤
        assert len(result.explanation_steps) >= 3

        # 应该包含复杂性分析
        step_descriptions = [step.description for step in result.explanation_steps]
        assert any("复杂" in desc or "分析" in desc for desc in step_descriptions)

    @pytest.mark.asyncio
    async def test_explanation_quality_improvement_suggestions(self):
        """测试质量改进建议生成"""
        explanation_steps = [
            ExplanationStep(
                step_number=1,
                explanation_type=ExplanationType.REASONING_PROCESS,
                title="低质量步骤",
                description="测试",
                confidence=0.3  # 低置信度
            )
        ]

        fusion_result = {
            "confidence": 0.4,
            "answer_quality_score": 0.3
        }

        explanation = await xai_service._explain_confidence(
            explanation_steps=explanation_steps,
            fusion_result=fusion_result
        )

        assert "improvement_suggestions" in explanation
        assert len(explanation["improvement_suggestions"]) > 0

        # 低质量应该有改进建议
        suggestions = explanation["improvement_suggestions"]
        assert any("改进" in suggestion or "提升" in suggestion for suggestion in suggestions)


class TestXAIIntegration:
    """XAI集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_explanation_workflow(self):
        """测试端到端解释工作流"""
        query = "分析我们公司第三季度的销售表现，包括与竞争对手的比较"

        # 模拟融合结果
        fusion_result = {
            "answer": "第三季度销售表现良好，同比增长15%，在竞争中处于领先地位。",
            "confidence": 0.87,
            "answer_quality_score": 0.83,
            "sources": [
                {"source_id": "sql_001", "confidence": 0.92, "name": "销售数据"},
                {"source_id": "rag_001", "confidence": 0.85, "name": "市场分析"}
            ],
            "conflicts": [],
            "processing_time": 3.2
        }

        # 模拟推理步骤
        reasoning_steps = [
            {
                "step_number": 1,
                "description": "理解查询意图和关键要素",
                "confidence": 0.95,
                "evidence": ["识别时间范围：Q3", "识别分析对象：销售表现", "识别对比维度：竞争对手"]
            }
        ]

        # 模拟数据源
        sources = [
            {
                "source_id": "sql_001",
                "source_type": "sql_query",
                "name": "销售数据库",
                "content": "Q3销售额：145万元，同比增长15%",
                "confidence": 0.92,
                "relevance_score": 0.95
            },
            {
                "source_id": "rag_001",
                "source_type": "rag_retrieval",
                "name": "市场分析报告",
                "content": "公司Q3市场份额提升2个百分点，超过主要竞争对手",
                "confidence": 0.85,
                "relevance_score": 0.88
            }
        ]

        result = await xai_service.generate_explanation(
            query=query,
            answer=fusion_result["answer"],
            fusion_result=fusion_result,
            reasoning_steps=reasoning_steps,
            sources=sources,
            tenant_id="integration_test"
        )

        # 验证完整工作流
        assert result is not None
        assert len(result.explanation_steps) > 0
        assert len(result.source_traces) == len(sources)
        assert result.confidence_explanation is not None
        assert result.uncertainty_quantification is not None
        assert result.visualization_data is not None

        # 验证质量
        assert result.explanation_quality_score > 0.7
        assert result.confidence_explanation["overall_confidence"] > 0.8

    @pytest.mark.asyncio
    async def test_multilingual_explanation(self):
        """测试多语言解释生成"""
        query = "What was the sales performance in Q3?"
        answer = "Q3 sales performance was excellent with 15% growth."

        sources = [
            {
                "source_id": "sql_001",
                "source_type": "sql_query",
                "name": "Sales Database",
                "content": "Q3 sales: $145,000, growth: 15%",
                "confidence": 0.92,
                "relevance_score": 0.95
            }
        ]

        result = await xai_service.generate_explanation(
            query=query,
            answer=answer,
            sources=sources,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.query == query
        assert result.answer == answer
        assert len(result.explanation_steps) > 0

    @pytest.mark.asyncio
    async def test_explanation_consistency(self):
        """测试解释一致性"""
        query = "简单测试查询"
        answer = "简单测试答案"

        # 多次生成解释，检查一致性
        results = []
        for i in range(3):
            result = await xai_service.generate_explanation(
                query=query,
                answer=answer,
                tenant_id=f"test_tenant_{i}"
            )
            results.append(result)

        # 检查基本一致性
        for result in results:
            assert result.query == query
            assert result.answer == answer
            assert len(result.explanation_steps) > 0

        # 检查步骤数量的一致性（应该有相同的基本步骤类型）
        step_types_sets = [
            {step.explanation_type for step in result.explanation_steps}
            for result in results
        ]

        # 所有结果应该包含相同的核心解释类型
        common_types = set.intersection(*step_types_sets)
        assert len(common_types) > 0