"""
XAI和融合引擎端到端集成测试
测试完整的从查询到可解释答案的工作流
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import json

from src.app.services.enhanced_reasoning_service import enhanced_reasoning_engine
from src.app.services.reasoning_service import ReasoningMode
from src.app.services.fusion_service import fusion_engine
from src.app.services.xai_service import xai_service


class TestXAIFusionIntegration:
    """XAI和融合引擎集成测试"""

    @pytest.fixture
    def realistic_sales_data(self) -> Dict[str, Any]:
        """真实的销售数据场景"""
        return {
            "query": "分析我们公司2024年第三季度的综合表现，包括销售数据、市场趋势、竞争对手对比，并提供改进建议",
            "sql_results": [
                {
                    "data": [
                        {"month": "July", "revenue": 285000, "profit": 72000, "orders": 1250},
                        {"month": "August", "revenue": 342000, "profit": 89500, "orders": 1480},
                        {"month": "September", "revenue": 298000, "profit": 78000, "orders": 1320}
                    ],
                    "query": "SELECT month, revenue, profit, orders FROM sales_metrics WHERE quarter = 'Q3' AND year = 2024",
                    "confidence": 0.96,
                    "execution_time": 180,
                    "database": "company_analytics"
                },
                {
                    "data": [
                        {"product_category": "电子产品", "q3_revenue": 156000, "growth_rate": 0.18},
                        {"product_category": "软件服务", "q3_revenue": 89000, "growth_rate": 0.12},
                        {"product_category": "咨询服务", "q3_revenue": 67000, "growth_rate": 0.08}
                    ],
                    "query": "SELECT product_category, q3_revenue, growth_rate FROM product_performance WHERE quarter = 'Q3'",
                    "confidence": 0.94,
                    "execution_time": 150,
                    "database": "product_db"
                }
            ],
            "rag_results": [
                {
                    "content": "根据2024年第三季度市场分析报告，整体行业增长率为11.2%，我们公司以15.8%的增长率表现优于行业平均水平。市场份额从第二季度的8.2%提升到9.1%。",
                    "similarity_score": 0.91,
                    "collection": "market_analysis_2024",
                    "chunk_id": "q3_market_overview",
                    "document_id": "market_report_q3_2024",
                    "confidence": 0.89
                },
                {
                    "content": "竞争对手分析显示：主要竞争对手TechCorp在Q3实现12%增长，但利润率下降至18%；新兴公司StartupX增长较快但基数较小；传统巨头LegacyCo市场份额持续下滑。我们在高端市场竞争力显著增强。",
                    "similarity_score": 0.87,
                    "collection": "competitor_intelligence",
                    "chunk_id": "q3_competitor_analysis",
                    "document_id": "competitor_report_2024_q3",
                    "confidence": 0.84
                },
                {
                    "content": "客户满意度调查显示Q3满意度达到4.6/5.0，较Q2提升0.3分。主要改进点：产品质量提升(89%客户满意)、服务响应速度(85%客户满意)、价格竞争力(78%客户满意)。",
                    "similarity_score": 0.83,
                    "collection": "customer_feedback",
                    "chunk_id": "satisfaction_survey_q3",
                    "document_id": "customer_satisfaction_2024",
                    "confidence": 0.81
                }
            ],
            "documents": [
                {
                    "title": "2024年第三季度战略执行评估",
                    "content": "本季度公司战略执行情况良好。新市场拓展计划完成度92%，数字化转型项目按计划推进，组织架构优化顺利完成。主要成就：华东市场份额突破10%，新产品线贡献率达到15%，运营效率提升12%。",
                    "file_name": "Q3_2024_Strategy_Execution.pdf",
                    "file_type": "pdf",
                    "page_number": 3,
                    "section": "executive_summary",
                    "confidence": 0.86
                },
                {
                    "title": "财务健康状况分析报告",
                    "content": "Q3财务状况稳健：现金流充足，负债率控制在35%的健康水平，应收账款周转率提升至4.2次/年。研发投入占比达到8.5%，为未来增长奠定基础。建议继续加强成本控制和现金流管理。",
                    "file_name": "Financial_Health_Analysis_Q3_2024.pdf",
                    "file_type": "pdf",
                    "page_number": 1,
                    "section": "summary",
                    "confidence": 0.88
                }
            ],
            "context": [
                {"role": "user", "content": "我们第二季度的表现如何？"},
                {"role": "assistant", "content": "第二季度表现良好，收入增长12%，利润增长10%，市场份额达到8.2%。"},
                {"role": "user", "content": "主要挑战是什么？"},
                {"role": "assistant", "content": "主要挑战包括成本控制、市场竞争加剧和供应链管理优化。"}
            ],
            "tenant_id": "integration_test_tenant"
        }

    @pytest.mark.asyncio
    async def test_complete_xai_fusion_workflow(self, realistic_sales_data):
        """测试完整的XAI融合工作流"""
        # 执行增强推理
        result = await enhanced_reasoning_engine.enhanced_reason(
            query=realistic_sales_data["query"],
            context=realistic_sales_data["context"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            documents=realistic_sales_data["documents"],
            tenant_id=realistic_sales_data["tenant_id"],
            reasoning_mode=ReasoningMode.ANALYTICAL,
            enable_fusion=True,
            enable_xai=True
        )

        # 验证基础结构完整性
        assert "query" in result
        assert "base_reasoning" in result
        assert "fusion_result" in result
        assert "xai_explanation" in result
        assert "enhanced_answer" in result
        assert "processing_metadata" in result
        assert "quality_metrics" in result

        # 验证内容质量
        assert result["query"] == realistic_sales_data["query"]
        assert len(result["enhanced_answer"]) > 300  # 应该是详细的综合性答案
        assert result["fusion_result"] is not None
        assert result["xai_explanation"] is not None

        # 验证融合结果质量
        fusion_result = result["fusion_result"]
        assert fusion_result.confidence > 0.8  # 高质量数据源应该产生高置信度
        assert fusion_result.answer_quality_score > 0.7
        assert fusion_result.source_count >= 5  # 应该融合多个数据源
        assert len(fusion_result.sources) >= 5

        # 验证XAI解释质量
        xai_result = result["xai_explanation"]
        assert xai_result.explanation_quality_score > 0.7
        assert len(xai_result.explanation_steps) >= 6  # 复杂查询应该有充分的解释
        assert len(xai_result.source_traces) >= 5
        assert xai_result.confidence_explanation is not None
        assert xai_result.uncertainty_quantification is not None

        # 验证质量指标
        quality_metrics = result["quality_metrics"]
        assert quality_metrics["overall_quality"] > 0.75
        assert quality_metrics["quality_grade"] in ["优秀", "良好"]
        assert quality_metrics["fusion_quality"] > 0.7
        assert quality_metrics["xai_quality"] > 0.7

        # 验证处理性能
        processing_metadata = result["processing_metadata"]
        assert processing_metadata["total_processing_time"] > 0
        assert processing_metadata["total_processing_time"] < 20  # 应该在20秒内完成
        assert processing_metadata["fusion_enabled"] is True
        assert processing_metadata["xai_enabled"] is True
        assert processing_metadata["reasoning_mode"] == "analytical"

    @pytest.mark.asyncio
    async def test_fusion_engine_standalone(self, realistic_sales_data):
        """测试独立的融合引擎"""
        fusion_result = await fusion_engine.fuse_multi_source_data(
            query=realistic_sales_data["query"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            documents=realistic_sales_data["documents"],
            context=realistic_sales_data["context"],
            tenant_id=realistic_sales_data["tenant_id"]
        )

        assert fusion_result is not None
        assert len(fusion_result.answer) > 200
        assert fusion_result.confidence > 0.7
        assert fusion_result.answer_quality_score > 0.6
        assert len(fusion_result.sources) >= 5
        assert fusion_result.processing_time > 0

    @pytest.mark.asyncio
    async def test_xai_service_standalone(self, realistic_sales_data):
        """测试独立的XAI服务"""
        xai_result = await xai_service.generate_explanation(
            query=realistic_sales_data["query"],
            answer="基于综合分析，第三季度表现优秀，收入、利润和市场份额均有显著提升。",
            sources=realistic_sales_data["rag_results"] + realistic_sales_data["documents"],
            tenant_id=realistic_sales_data["tenant_id"]
        )

        assert xai_result is not None
        assert xai_result.query == realistic_sales_data["query"]
        assert len(xai_result.explanation_steps) > 0
        assert len(xai_result.source_traces) > 0
        assert xai_result.confidence_explanation is not None
        assert xai_result.uncertainty_quantification is not None
        assert xai_result.explanation_quality_score > 0

    @pytest.mark.asyncio
    async def test_conflict_handling_integration(self):
        """测试冲突处理的集成"""
        # 创建冲突的数据源
        conflicting_sql_results = [
            {
                "data": [{"revenue": 285000}],
                "query": "Q7收入查询",
                "confidence": 0.9
            },
            {
                "data": [{"revenue": 295000}],  # 冲突数据
                "query": "Q7收入验证查询",
                "confidence": 0.8
            }
        ]

        rag_results = [
            {
                "content": "第三季度收入约为29万元",
                "similarity_score": 0.85,
                "confidence": 0.82
            }
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="第三季度的收入是多少？",
            sql_results=conflicting_sql_results,
            rag_results=rag_results,
            tenant_id="conflict_test_tenant"
        )

        # 即使有冲突，也应该能生成答案
        assert result is not None
        assert result["enhanced_answer"] is not None

        if result["fusion_result"]:
            # 检查冲突处理
            if result["fusion_result"].conflicts:
                assert len(result["fusion_result"].conflicts) > 0
                # 冲突应该被解决
                for conflict in result["fusion_result"].conflicts:
                    assert conflict.resolution_result is not None

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, realistic_sales_data):
        """测试多租户隔离"""
        tenant_1 = "tenant_1"
        tenant_2 = "tenant_2"

        # 为不同租户生成结果
        result_1 = await enhanced_reasoning_engine.enhanced_reason(
            query=realistic_sales_data["query"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            tenant_id=tenant_1
        )

        result_2 = await enhanced_reasoning_engine.enhanced_reason(
            query=realistic_sales_data["query"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            tenant_id=tenant_2
        )

        # 验证租户隔离
        assert result_1 is not None
        assert result_2 is not None
        assert result_1["processing_metadata"]["tenant_id"] == tenant_1
        assert result_2["processing_metadata"]["tenant_id"] == tenant_2

        # 验证结果独立性（即使查询相同，处理时间可能不同）
        assert result_1["processing_metadata"]["total_processing_time"] != result_2["processing_metadata"]["total_processing_time"]

    @pytest.mark.asyncio
    async def test_performance_benchmark(self, realistic_sales_data):
        """测试性能基准"""
        queries = [
            realistic_sales_data["query"],
            "分析产品类别的表现",
            "评估市场趋势",
            "对比竞争对手",
            "总结改进建议"
        ]

        # 批量执行查询
        start_time = datetime.utcnow()

        tasks = []
        for i, query in enumerate(queries):
            task = enhanced_reasoning_engine.enhanced_reason(
                query=query,
                sql_results=realistic_sales_data["sql_results"],
                rag_results=realistic_sales_data["rag_results"],
                tenant_id=f"perf_tenant_{i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        # 性能验证
        assert len(results) == len(queries)
        assert total_time < 60  # 5个查询应该在60秒内完成

        # 统计性能指标
        processing_times = [r["processing_metadata"]["total_processing_time"] for r in results]
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)

        # 性能断言
        assert avg_time < 10  # 平均处理时间小于10秒
        assert max_time < 20  # 最大处理时间小于20秒
        assert min_time > 0  # 最小处理时间大于0

        # 质量验证
        quality_scores = [r["quality_metrics"]["overall_quality"] for r in results]
        avg_quality = sum(quality_scores) / len(quality_scores)
        assert avg_quality > 0.6  # 平均质量应该大于0.6

    @pytest.mark.asyncio
    async def test_scalability_with_large_dataset(self):
        """测试大数据集的可扩展性"""
        # 创建大量数据源
        large_sql_results = []
        for i in range(20):
            large_sql_results.append({
                "data": [{"category": f"分类{i}", "value": i * 1000}],
                "query": f"SELECT * FROM category_{i}",
                "confidence": 0.85 + (i % 10) * 0.01
            })

        large_rag_results = []
        for i in range(15):
            large_rag_results.append({
                "content": f"这是第{i}个RAG检索结果，包含相关信息。",
                "similarity_score": 0.8 + (i % 5) * 0.02,
                "confidence": 0.75 + (i % 8) * 0.02
            })

        large_documents = []
        for i in range(10):
            large_documents.append({
                "title": f"文档{i}",
                "content": f"这是第{i}个文档的内容，包含相关分析数据。",
                "confidence": 0.7 + (i % 6) * 0.03
            })

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="分析所有分类的综合表现",
            sql_results=large_sql_results,
            rag_results=large_rag_results,
            documents=large_documents,
            tenant_id="scalability_test"
        )

        # 验证大数据集处理
        assert result is not None
        assert result["enhanced_answer"] is not None

        if result["fusion_result"]:
            assert result["fusion_result"].source_count >= 20  # 应该处理大量数据源

        # 验证性能合理性
        processing_time = result["processing_metadata"]["total_processing_time"]
        assert processing_time < 30  # 即使大数据集也应该在合理时间内完成

    @pytest.mark.asyncio
    async def test_error_resilience_robustness(self):
        """测试错误弹性和鲁棒性"""
        # 混合正常和异常的数据
        mixed_sql_results = [
            {"data": [{"value": 1000}], "confidence": 0.9},  # 正常数据
            None,  # None值
            {"data": None, "confidence": 0.8},  # 空数据
            {"confidence": 0.7},  # 缺少data字段
            {"data": [{"value": 2000}], "confidence": 0.85}  # 正常数据
        ]

        mixed_rag_results = [
            {
                "content": "正常RAG结果",
                "similarity_score": 0.9,
                "confidence": 0.85
            },
            {},  # 空结果
            {"content": "", "similarity_score": 0.0, "confidence": 0.0},  # 无效内容
            {
                "content": "另一个正常结果",
                "similarity_score": 0.8,
                "confidence": 0.8
            }
        ]

        result = await enhanced_reasoning_engine.enhanced_reason(
            query="测试错误处理",
            sql_results=mixed_sql_results,
            rag_results=mixed_rag_results,
            tenant_id="error_test_tenant"
        )

        # 即使有异常数据，也应该能够生成答案
        assert result is not None
        assert result["enhanced_answer"] is not None
        assert len(result["enhanced_answer"]) > 0

        # 验证错误处理
        if result["processing_metadata"].get("fallback_to_base"):
            assert result["base_reasoning"] is not None

    @pytest.mark.asyncio
    async def test_explanation_transparency_and_trust(self, realistic_sales_data):
        """测试解释透明度和信任度"""
        result = await enhanced_reasoning_engine.enhanced_reason(
            query=realistic_sales_data["query"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            documents=realistic_sales_data["documents"],
            tenant_id="transparency_test"
        )

        # 验证XAI解释的透明度
        xai_result = result["xai_explanation"]
        assert xai_result is not None

        # 检查解释步骤的透明性
        explanation_steps = xai_result.explanation_steps
        assert len(explanation_steps) > 0

        for step in explanation_steps:
            assert step.title is not None
            assert step.description is not None
            assert step.confidence >= 0
            assert step.confidence <= 1
            assert step.timestamp is not None

        # 检查源数据追踪的透明性
        source_traces = xai_result.source_traces
        assert len(source_traces) > 0

        for trace in source_traces:
            assert trace.source_id is not None
            assert trace.source_type is not None
            assert trace.source_name is not None
            assert trace.content_snippet is not None
            assert 0 <= trace.relevance_score <= 1
            assert 0 <= trace.confidence_contribution <= 1
            assert trace.verification_status is not None

        # 检查置信度解释的透明性
        confidence_explanation = xai_result.confidence_explanation
        assert confidence_explanation is not None
        assert "overall_confidence" in confidence_explanation
        assert "confidence_factors" in confidence_explanation
        assert "confidence_description" in confidence_explanation

        # 检查不确定性量化的透明性
        uncertainty_quant = xai_result.uncertainty_quantification
        assert uncertainty_quant is not None
        assert 0 <= uncertainty_quant.total_uncertainty <= 1
        assert uncertainty_quant.uncertainty_sources is not None
        assert uncertainty_quant.mitigation_suggestions is not None

    @pytest.mark.asyncio
    async def test_end_to_end_quality_assurance(self, realistic_sales_data):
        """测试端到端质量保证"""
        result = await enhanced_reasoning_engine.enhanced_reason(
            query=realistic_sales_data["query"],
            context=realistic_sales_data["context"],
            sql_results=realistic_sales_data["sql_results"],
            rag_results=realistic_sales_data["rag_results"],
            documents=realistic_sales_data["documents"],
            tenant_id="quality_assurance_tenant",
            reasoning_mode=ReasoningMode.CONTEXT_AWARE
        )

        # 综合质量评估
        quality_metrics = result["quality_metrics"]

        # 基础推理质量
        assert quality_metrics.get("base_reasoning_quality", 0) > 0.3

        # 融合质量
        if "fusion_quality" in quality_metrics:
            assert quality_metrics["fusion_quality"] > 0.5

        # XAI质量
        if "xai_quality" in quality_metrics:
            assert quality_metrics["xai_quality"] > 0.5

        # 整体质量
        overall_quality = quality_metrics["overall_quality"]
        assert overall_quality > 0.5
        assert quality_metrics["quality_grade"] in ["优秀", "良好", "一般"]

        # 验证答案质量
        answer = result["enhanced_answer"]
        assert len(answer) > 100  # 应该有足够的长度
        assert realistic_sales_data["query"][:10] not in answer  # 不应该简单重复查询

        # 验证多源数据融合
        if result["fusion_result"]:
            fusion = result["fusion_result"]
            assert fusion.confidence > 0.5
            assert fusion.answer_quality_score > 0.4
            assert len(fusion.sources) > 0

        # 验证解释质量
        if result["xai_explanation"]:
            xai = result["xai_explanation"]
            assert xai.explanation_quality_score > 0.3
            assert len(xai.explanation_steps) > 0
            assert len(xai.source_traces) > 0

    @pytest.mark.asyncio
    async def test_concurrent_multi_user_scenario(self, realistic_sales_data):
        """测试并发多用户场景"""
        # 模拟10个并发用户
        user_queries = [
            "我的销售表现如何？",
            "市场趋势是什么？",
            "竞争对手在做什么？",
            "我该如何改进？",
            "财务状况怎么样？",
            "客户满意度如何？",
            "产品表现分析",
            "未来预测建议",
            "风险评估",
            "战略规划建议"
        ]

        # 为每个用户创建并发任务
        tasks = []
        for i, query in enumerate(user_queries):
            task = enhanced_reasoning_engine.enhanced_reason(
                query=query,
                sql_results=realistic_sales_data["sql_results"],
                rag_results=realistic_sales_data["rag_results"],
                tenant_id=f"user_{i}"
            )
            tasks.append(task)

        # 并发执行所有任务
        start_time = datetime.utcnow()
        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()

        total_time = (end_time - start_time).total_seconds()

        # 验证并发处理结果
        assert len(results) == len(user_queries)

        # 验证每个结果的质量
        for i, result in enumerate(results):
            assert result is not None
            assert result["enhanced_answer"] is not None
            assert result["query"] == user_queries[i]
            assert result["processing_metadata"]["tenant_id"] == f"user_{i}"

        # 验证并发性能
        assert total_time < 45  # 10个并发查询应该在45秒内完成
        avg_time = total_time / len(user_queries)
        assert avg_time < 8  # 平均每个查询8秒内完成

    @pytest.mark.asyncio
    async def test_integration_with_external_apis(self):
        """测试与外部API的集成"""
        # 模拟需要外部API数据的场景
        result = await enhanced_reasoning_engine.enhanced_reason(
            query="获取最新的市场数据和行业趋势",
            tenant_id="api_integration_test",
            enable_fusion=True,
            enable_xai=True
        )

        # 即使没有外部数据，也应该能够处理
        assert result is not None
        assert result["enhanced_answer"] is not None

        # 验证错误处理和回退机制
        if result["processing_metadata"].get("fallback_to_base"):
            assert result["base_reasoning"] is not None