"""
增强推理服务测试
测试融合引擎和XAI功能的集成
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import json

from src.app.services.reasoning_service import (
    enhanced_reasoning_engine,
    EnhancedReasoningEngine,
    ReasoningMode,
    QueryType
)


class TestEnhancedReasoningEngine:
    """增强推理引擎测试类"""

    @pytest.fixture
    def sample_sql_results(self) -> List[Dict[str, Any]]:
        """示例SQL查询结果"""
        return [
            {
                "data": [
                    {"product": "产品A", "sales": 120000, "quarter": "Q3"},
                    {"product": "产品B", "sales": 80000, "quarter": "Q3"}
                ],
                "query": "SELECT product, sales FROM sales_data WHERE quarter = 'Q3'",
                "confidence": 0.95,
                "execution_time": 150,
                "database": "analytics_db"
            }
        ]

    @pytest.fixture
    def sample_rag_results(self) -> List[Dict[str, Any]]:
        """示例RAG检索结果"""
        return [
            {
                "content": "根据年度报告显示，第三季度产品A的销售表现超出预期，达到了12万元的销售额。",
                "similarity_score": 0.92,
                "collection": "annual_reports",
                "chunk_id": "chunk_001",
                "document_id": "doc_001",
                "confidence": 0.88
            }
        ]

    @pytest.fixture
    def sample_documents(self) -> List[Dict[str, Any]]:
        """示例文档数据"""
        return [
            {
                "title": "2024年第三季度财务报告",
                "content": "本季度总收入为20万元，同比增长15%。主要产品线表现良好。",
                "file_name": "Q3_2024_financial_report.pdf",
                "file_type": "pdf",
                "page_number": 1,
                "section": "executive_summary",
                "confidence": 0.85
            }
        ]

    @pytest.mark.asyncio
    async def test_enhanced_reasoning_basic(
        self,
        sample_sql_results,
        sample_rag_results,
        sample_documents
    ):
        """测试基本增强推理功能"""
        query = "第三季度的销售情况如何？"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sample_sql_results,
            rag_results=sample_rag_results,
            documents=sample_documents,
            tenant_id="test_tenant",
            enable_fusion=True,
            enable_xai=True
        )

        # 验证基本结构
        assert "query" in result
        assert "base_reasoning" in result
        assert "fusion_result" in result
        assert "xai_explanation" in result
        assert "enhanced_answer" in result
        assert "processing_metadata" in result
        assert "quality_metrics" in result

        # 验证内容
        assert result["query"] == query
        assert result["enhanced_answer"] is not None
        assert len(result["enhanced_answer"]) > 0

        # 验证融合结果
        assert result["fusion_result"] is not None

        # 验证XAI解释
        assert result["xai_explanation"] is not None

    @pytest.mark.asyncio
    async def test_enhanced_reasoning_without_fusion(self):
        """测试禁用融合功能的增强推理"""
        query = "简单测试查询"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            tenant_id="test_tenant",
            enable_fusion=False,
            enable_xai=True
        )

        assert result is not None
        assert result["fusion_result"] is None  # 融合应该被禁用
        assert result["xai_explanation"] is not None  # XAI应该仍然启用
        assert result["enhanced_answer"] is not None

    @pytest.mark.asyncio
    async def test_enhanced_reasoning_without_xai(self, sample_sql_results):
        """测试禁用XAI功能的增强推理"""
        query = "测试查询"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sample_sql_results,
            tenant_id="test_tenant",
            enable_fusion=True,
            enable_xai=False
        )

        assert result is not None
        assert result["fusion_result"] is not None  # 融合应该启用
        assert result["xai_explanation"] is None  # XAI应该被禁用
        assert result["enhanced_answer"] is not None

    @pytest.mark.asyncio
    async def test_enhanced_reasoning_with_context(self, sample_sql_results):
        """测试带上下文的增强推理"""
        query = "当前的销售趋势如何？"
        context = [
            {"role": "user", "content": "之前我们讨论了第二季度的表现"},
            {"role": "assistant", "content": "第二季度销售额为18万元"}
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            context=context,
            sql_results=sample_sql_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result["enhanced_answer"] is not None
        # 上下文应该影响答案生成
        assert len(result["enhanced_answer"]) > 0

    @pytest.mark.asyncio
    async def test_enhanced_reasoning_with_reasoning_mode(self, sample_sql_results):
        """测试指定推理模式的增强推理"""
        query = "分析销售数据"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sample_sql_results,
            tenant_id="test_tenant",
            reasoning_mode=ReasoningMode.ANALYTICAL
        )

        assert result is not None
        assert result["processing_metadata"]["reasoning_mode"] == "analytical"

    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, sample_sql_results, sample_rag_results):
        """测试质量指标计算"""
        query = "综合分析查询"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sample_sql_results,
            rag_results=sample_rag_results,
            tenant_id="test_tenant"
        )

        assert "quality_metrics" in result
        metrics = result["quality_metrics"]

        # 应该包含基础推理质量指标
        assert "base_reasoning_quality" in metrics
        assert "base_reasoning_confidence" in metrics

        # 应该包含融合质量指标（如果融合启用）
        if result["fusion_result"]:
            assert "fusion_quality" in metrics
            assert "fusion_confidence" in metrics
            assert "source_count" in metrics
            assert "conflict_count" in metrics

        # 应该包含XAI质量指标（如果XAI启用）
        if result["xai_explanation"]:
            assert "xai_quality" in metrics
            assert "explanation_steps" in metrics
            assert "source_traces" in metrics

        # 应该包含综合质量分数
        assert "overall_quality" in metrics
        assert 0 <= metrics["overall_quality"] <= 1

        # 应该包含质量等级
        assert "quality_grade" in metrics
        assert metrics["quality_grade"] in ["优秀", "良好", "一般", "需要改进"]

    @pytest.mark.asyncio
    async def test_fusion_answer_override(self, sample_sql_results):
        """测试融合答案覆盖机制"""
        query = "测试查询"

        # 模拟高质量的融合结果
        high_quality_fusion_data = {
            "answer": "这是高质量的融合答案",
            "answer_quality_score": 0.9,  # 高质量分数
            "confidence": 0.85
        }

        # 创建一个模拟的融合结果
        engine = EnhancedReasoningEngine()

        # 先获取基础推理结果
        base_result = await engine.base_engine.reason(
            query=query,
            tenant_id="test_tenant"
        )

        # 模拟融合质量更高的情况
        enhanced_result = {
            "query": query,
            "base_reasoning": base_result,
            "enhanced_answer": base_result.answer,
            "fusion_result": high_quality_fusion_data,
            "processing_metadata": {}
        }

        # 计算质量指标
        metrics = engine._calculate_quality_metrics(enhanced_result)

        # 验证质量计算正确
        assert "fusion_quality" in metrics
        assert metrics["fusion_quality"] == 0.9

    @pytest.mark.asyncio
    async def test_data_sources_preparation(self, sample_sql_results, sample_rag_results, sample_documents):
        """测试数据源准备功能"""
        engine = EnhancedReasoningEngine()

        base_sources = engine._prepare_data_sources(
            sample_sql_results,
            sample_rag_results,
            sample_documents
        )

        assert len(base_sources) == len(sample_sql_results) + len(sample_rag_results) + len(sample_documents)

        # 检查SQL源
        sql_sources = [s for s in base_sources if s["type"] == "sql_query"]
        assert len(sql_sources) == len(sample_sql_results)

        # 检查RAG源
        rag_sources = [s for s in base_sources if s["type"] == "rag_retrieval"]
        assert len(rag_sources) == len(sample_rag_results)

        # 检查文档源
        doc_sources = [s for s in base_sources if s["type"] == "document"]
        assert len(doc_sources) == len(sample_documents)

    @pytest.mark.asyncio
    async def test_sources_for_xai_preparation(self, sample_sql_results, sample_rag_results):
        """测试XAI数据源准备功能"""
        engine = EnhancedReasoningEngine()

        xai_sources = engine._prepare_sources_for_xai(
            sample_sql_results,
            sample_rag_results,
            []
        )

        assert len(xai_sources) == len(sample_sql_results) + len(sample_rag_results)

        for source in xai_sources:
            assert "source_id" in source
            assert "source_type" in source
            assert "name" in source
            assert "content" in source
            assert "confidence" in source
            assert "relevance_score" in source
            assert "metadata" in source

    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """测试错误处理和回退机制"""
        query = "测试错误处理"

        # 模拟错误情况（例如无效的数据源）
        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=None,  # 传入None可能导致错误
            rag_results=None,
            documents=None,
            tenant_id="test_tenant"
        )

        # 即使出错，也应该返回基础推理结果
        assert result is not None
        assert result["enhanced_answer"] is not None
        assert result["base_reasoning"] is not None
        assert result["processing_metadata"]["fallback_to_base"] is not None

    @pytest.mark.asyncio
    async def test_empty_inputs_handling(self):
        """测试空输入处理"""
        query = ""

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=[],
            rag_results=[],
            documents=[],
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result["enhanced_answer"] is not None

    @pytest.mark.asyncio
    async def test_reasoning_capabilities(self):
        """测试推理能力查询"""
        capabilities = await enhanced_reasoning_engine.get_reasoning_capabilities()

        assert "reasoning_modes" in capabilities
        assert "query_types" in capabilities
        assert "supported_features" in capabilities
        assert "fusion_algorithms" in capabilities
        assert "xai_types" in capabilities
        assert "visualization_types" in capabilities

        # 验证具体能力
        assert ReasoningMode.ANALYTICAL.value in capabilities["reasoning_modes"]
        assert QueryType.FACTUAL.value in capabilities["query_types"]
        assert capabilities["supported_features"]["multi_source_fusion"] is True
        assert capabilities["supported_features"]["xai_explanation"] is True
        assert capabilities["supported_features"]["conflict_resolution"] is True

    @pytest.mark.asyncio
    async def test_benchmark_reasoning(self):
        """测试推理性能基准"""
        test_queries = [
            "简单查询1",
            "简单查询2",
            "分析复杂查询"
        ]

        benchmark_results = await enhanced_reasoning_engine.benchmark_reasoning(
            test_queries=test_queries,
            tenant_id="benchmark_test"
        )

        assert "test_queries_count" in benchmark_results
        assert "results" in benchmark_results
        assert "performance_metrics" in benchmark_results

        assert benchmark_results["test_queries_count"] == len(test_queries)
        assert len(benchmark_results["results"]) == len(test_queries)

        # 检查性能指标
        perf_metrics = benchmark_results["performance_metrics"]
        assert "average_processing_time" in perf_metrics
        assert "average_quality_score" in perf_metrics
        assert "success_rate" in perf_metrics

        # 验证结果结构
        for result in benchmark_results["results"]:
            assert "query_index" in result
            assert "query" in result
            assert "processing_time" in result
            assert "quality_score" in result
            assert "success" in result

    @pytest.mark.asyncio
    async def test_multimodal_data_handling(self):
        """测试多模态数据处理"""
        # 模拟包含图像的RAG结果
        multimodal_rag_results = [
            {
                "content": [
                    {"type": "text", "text": "销售图表显示第三季度表现良好"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
                ],
                "similarity_score": 0.88,
                "collection": "quarterly_reports",
                "chunk_id": "chunk_001",
                "confidence": 0.85
            }
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="分析销售图表",
            rag_results=multimodal_rag_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result["enhanced_answer"] is not None

    @pytest.mark.asyncio
    async def test_large_dataset_processing(self):
        """测试大数据集处理"""
        # 创建大量SQL结果
        large_sql_results = []
        for i in range(10):
            large_sql_results.append({
                "data": [{"product": f"产品{i}", "sales": i * 1000}],
                "query": f"SELECT * FROM products WHERE id = {i}",
                "confidence": 0.9
            })

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="分析所有产品销售数据",
            sql_results=large_sql_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result["processing_metadata"]["total_processing_time"] > 0
        # 大数据集处理应该有合理的时间
        assert result["processing_metadata"]["total_processing_time"] < 30  # 30秒内完成

    @pytest.mark.asyncio
    async def test_concurrent_reasoning(self):
        """测试并发推理处理"""
        queries = [
            "查询1：第三季度销售",
            "查询2：市场分析",
            "查询3：竞争对手对比"
        ]

        # 并发执行多个推理任务
        tasks = []
        for query in queries:
            task = enhanced_reasoning_engine.enhanced_reason(
                query=query,
                tenant_id="concurrent_test"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == len(queries)

        for i, result in enumerate(results):
            assert result is not None
            assert result["query"] == queries[i]
            assert result["enhanced_answer"] is not None

    @pytest.mark.asyncio
    async def test_reasoning_mode_impact(self, sample_sql_results):
        """测试不同推理模式的影响"""
        query = "详细分析销售数据"

        modes = [ReasoningMode.BASIC, ReasoningMode.ANALYTICAL, ReasoningMode.STEP_BY_STEP]
        results = {}

        for mode in modes:
            result = await enhanced_reasoning_engine.enhanced_reason(
                query=query,
                sql_results=sample_sql_results,
                tenant_id="mode_test",
                reasoning_mode=mode
            )
            results[mode.value] = result

        # 验证不同模式产生不同的处理元数据
        for mode_value, result in results.items():
            assert result["processing_metadata"]["reasoning_mode"] == mode_value

    @pytest.mark.asyncio
    async def test_conflict_impact_on_quality(self):
        """测试冲突对质量的影响"""
        # 创建冲突的数据源
        conflicting_sql_results = [
            {"data": [{"sales": 120000}], "confidence": 0.9},
            {"data": [{"sales": 100000}], "confidence": 0.8}  # 冲突数据
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="销售数据",
            sql_results=conflicting_sql_results,
            tenant_id="conflict_test"
        )

        assert result is not None

        if result["fusion_result"]:
            # 检查是否检测到冲突
            assert "conflict_count" in result["quality_metrics"]

    @pytest.mark.asyncio
    async def test_xai_quality_threshold(self, sample_sql_results):
        """测试XAI质量阈值处理"""
        query = "测试查询"

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            sql_results=sample_sql_results,
            tenant_id="quality_test"
        )

        # XAI质量分数应该被正确计算
        if result["xai_explanation"]:
            assert 0 <= result["xai_explanation"].explanation_quality_score <= 1
            # 如果质量较低，应该有相应处理
            if result["xai_explanation"].explanation_quality_score < 0.5:
                # 这可能在日志中产生警告
                pass


class TestEnhancedReasoningIntegration:
    """增强推理集成测试"""

    @pytest.mark.asyncio
    async def test_real_world_complex_scenario(self):
        """测试真实世界复杂场景"""
        query = "分析我们公司2024年第三季度的综合表现，包括财务数据、市场趋势、竞争对手对比和未来预测，并提供详细的改进建议。"

        # 模拟复杂的数据源
        sql_results = [
            {
                "data": [
                    {"month": "July", "revenue": 45000, "profit": 12000},
                    {"month": "August", "revenue": 52000, "profit": 15000},
                    {"month": "September", "revenue": 48000, "profit": 13500}
                ],
                "confidence": 0.95
            }
        ]

        rag_results = [
            {
                "content": "根据市场研究，第三季度行业整体增长12%，公司表现优于行业平均水平。",
                "similarity_score": 0.92,
                "confidence": 0.88
            },
            {
                "content": "主要竞争对手A在第三季度实现8%增长，竞争对手B出现3%下降。",
                "similarity_score": 0.89,
                "confidence": 0.85
            }
        ]

        documents = [
            {
                "title": "Q3战略执行报告",
                "content": "公司在第三季度成功实施了新的营销策略，客户满意度提升15%。",
                "confidence": 0.82
            },
            {
                "title": "竞争对手分析报告",
                "content": "竞争对手在产品创新方面投入增加，我们需要加强研发投入。",
                "confidence": 0.78
            }
        ]

        # 上下文对话历史
        context = [
            {"role": "user", "content": "我们第二季度的表现如何？"},
            {"role": "assistant", "content": "第二季度表现良好，收入增长10%，利润增长8%。"}
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query=query,
            context=context,
            sql_results=sql_results,
            rag_results=rag_results,
            documents=documents,
            tenant_id="integration_test",
            reasoning_mode=ReasoningMode.ANALYTICAL,
            enable_fusion=True,
            enable_xai=True
        )

        # 验证综合结果
        assert result is not None
        assert len(result["enhanced_answer"]) > 200  # 应该是详细的答案

        # 验证多源融合
        assert result["fusion_result"] is not None
        assert result["fusion_result"].source_count >= 3

        # 验证XAI解释
        assert result["xai_explanation"] is not None
        assert len(result["xai_explanation"].explanation_steps) >= 5  # 复杂查询应该有更多步骤

        # 验证质量指标
        assert result["quality_metrics"]["overall_quality"] > 0.7  # 综合质量应该较高

        # 验证处理时间合理
        assert result["processing_metadata"]["total_processing_time"] < 15  # 15秒内完成

    @pytest.mark.asyncio
    async def test_performance_optimization(self):
        """测试性能优化"""
        queries = ["快速查询1", "快速查询2", "快速查询3", "快速查询4", "快速查询5"]

        # 测试批量处理性能
        start_time = datetime.utcnow()

        tasks = [
            enhanced_reasoning_engine.enhanced_reason(
                query=q,
                tenant_id="perf_test"
            )
            for q in queries
        ]

        results = await asyncio.gather(*tasks)

        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        # 验证所有查询都成功处理
        assert len(results) == len(queries)
        for result in results:
            assert result is not None
            assert result["enhanced_answer"] is not None

        # 验证总体性能（5个查询应该在合理时间内完成）
        assert total_time < 30  # 30秒内完成5个查询

        # 验证平均处理时间
        avg_time = total_time / len(queries)
        assert avg_time < 6  # 平均每个查询6秒内完成

    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self):
        """测试错误恢复和弹性"""
        # 测试部分数据源失败的情况
        valid_sql_results = [
            {"data": [{"sales": 100000}], "confidence": 0.9}
        ]

        # 模拟有问题的RAG结果
        problematic_rag_results = [
            None,  # 无效结果
            {"content": "", "similarity_score": 0.0},  # 空结果
            {"content": "有效的RAG结果", "similarity_score": 0.8, "confidence": 0.75}
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="弹性测试查询",
            sql_results=valid_sql_results,
            rag_results=problematic_rag_results,
            tenant_id="resilience_test"
        )

        # 即使有部分数据源失败，也应该能够生成答案
        assert result is not None
        assert result["enhanced_answer"] is not None
        assert len(result["enhanced_answer"]) > 0

        # 验证使用了有效数据
        if result["fusion_result"]:
            assert result["fusion_result"].source_count >= 1