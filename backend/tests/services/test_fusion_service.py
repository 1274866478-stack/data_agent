"""
融合引擎服务测试
测试多源数据融合、冲突解决和质量评估功能
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import json

from src.app.services.fusion_service import (
    fusion_engine,
    DataFusionEngine,
    DataSourceType,
    ConflictResolutionStrategy,
    SourceData,
    ConflictInfo,
    FusionResult
)


class TestDataFusionEngine:
    """融合引擎测试类"""

    @pytest.fixture
    def sample_sql_results(self) -> List[Dict[str, Any]]:
        """示例SQL查询结果"""
        return [
            {
                "data": [
                    {"product": "产品A", "sales": 1200, "quarter": "Q3"},
                    {"product": "产品B", "sales": 800, "quarter": "Q3"}
                ],
                "query": "SELECT product, sales FROM sales_data WHERE quarter = 'Q3'",
                "confidence": 0.95,
                "execution_time": 150,
                "database": "analytics_db"
            },
            {
                "data": [
                    {"month": "July", "revenue": 45000},
                    {"month": "August", "revenue": 52000},
                    {"month": "September", "revenue": 48000}
                ],
                "query": "SELECT month, revenue FROM monthly_revenue WHERE quarter = 'Q3'",
                "confidence": 0.90,
                "execution_time": 120,
                "database": "finance_db"
            }
        ]

    @pytest.fixture
    def sample_rag_results(self) -> List[Dict[str, Any]]:
        """示例RAG检索结果"""
        return [
            {
                "content": "根据年度报告显示，第三季度产品A的销售表现超出预期，达到了1200单位的销售量。",
                "similarity_score": 0.92,
                "collection": "annual_reports",
                "chunk_id": "chunk_001",
                "document_id": "doc_001",
                "confidence": 0.88
            },
            {
                "content": "市场分析报告指出，Q3期间产品B的市场份额有所下降，但整体利润率保持稳定。",
                "similarity_score": 0.85,
                "collection": "market_analysis",
                "chunk_id": "chunk_042",
                "document_id": "doc_015",
                "confidence": 0.82
            }
        ]

    @pytest.fixture
    def sample_documents(self) -> List[Dict[str, Any]]:
        """示例文档数据"""
        return [
            {
                "title": "2024年第三季度财务报告",
                "content": "本季度总收入为145,000元，同比增长15%。主要产品线表现良好。",
                "file_name": "Q3_2024_financial_report.pdf",
                "file_type": "pdf",
                "page_number": 1,
                "section": "executive_summary",
                "confidence": 0.85
            }
        ]

    @pytest.fixture
    def conflicting_sql_results(self) -> List[Dict[str, Any]]:
        """冲突的SQL查询结果（用于测试冲突检测）"""
        return [
            {
                "data": [{"sales": 1200}],
                "confidence": 0.9
            },
            {
                "data": [{"sales": 1100}],
                "confidence": 0.8
            }
        ]

    @pytest.mark.asyncio
    async def test_fuse_multi_source_data_basic(
        self,
        sample_sql_results,
        sample_rag_results,
        sample_documents
    ):
        """测试基本的多源数据融合"""
        query = "第三季度的销售情况如何？"

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            sql_results=sample_sql_results,
            rag_results=sample_rag_results,
            documents=sample_documents,
            tenant_id="test_tenant"
        )

        assert isinstance(result, FusionResult)
        assert result.answer is not None
        assert len(result.answer) > 0
        assert result.confidence > 0
        assert result.fusion_metadata is not None
        assert result.processing_time > 0
        assert result.answer_quality_score >= 0

        # 检查源信息
        assert len(result.sources) > 0
        assert result.fusion_metadata["source_count"] > 0

    @pytest.mark.asyncio
    async def test_fuse_sql_only_data(self, sample_sql_results):
        """测试仅SQL数据的融合"""
        query = "产品A的销售数据是什么？"

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            sql_results=sample_sql_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.answer is not None
        # 应该包含产品A的销售信息
        assert "产品A" in result.answer or "1200" in result.answer

    @pytest.mark.asyncio
    async def test_fuse_rag_only_data(self, sample_rag_results):
        """测试仅RAG数据的融合"""
        query = "第三季度的市场表现如何？"

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            rag_results=sample_rag_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.answer is not None
        assert len(result.sources) == len(sample_rag_results)

    @pytest.mark.asyncio
    async def test_fuse_empty_data_sources(self):
        """测试空数据源的融合"""
        query = "这是一个测试查询"

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.answer is not None
        # 应该返回默认答案
        assert "数据融合" in result.answer or "问题" in result.answer

    @pytest.mark.asyncio
    async def test_conflict_detection(self, conflicting_sql_results):
        """测试冲突检测功能"""
        engine = DataFusionEngine()

        # 标准化输入数据
        source_data_list = await engine._standardize_input_data(
            conflicting_sql_results, [], []
        )

        # 预处理数据
        processed_data = await engine._preprocess_data(source_data_list)

        # 检测冲突
        conflicts = await engine._detect_conflicts(processed_data)

        assert len(conflicts) > 0
        assert any(c.conflict_type == "numeric_conflict" for c in conflicts)

    @pytest.mark.asyncio
    async def test_conflict_resolution_sql_priority(self, conflicting_sql_results):
        """测试SQL优先的冲突解决策略"""
        engine = DataFusionEngine()

        # 标准化输入数据
        source_data_list = await engine._standardize_input_data(
            conflicting_sql_results, [], []
        )

        # 预处理数据
        processed_data = await engine._preprocess_data(source_data_list)

        # 创建冲突
        conflicts = [
            ConflictInfo(
                conflict_type="numeric_conflict",
                conflicting_sources=["sql_0", "sql_1"],
                conflict_description="数值不一致",
                resolution_strategy=ConflictResolutionStrategy.TRUST_SQL_OVER_RAG,
                resolution_result="pending",
                confidence_impact=0.2
            )
        ]

        # 解决冲突
        resolved_data = await engine._resolve_conflicts(processed_data, conflicts)

        assert len(resolved_data) == len(processed_data)
        assert conflicts[0].resolution_result != "resolution_failed"

    @pytest.mark.asyncio
    async def test_conflict_resolution_by_confidence(self):
        """测试基于置信度的冲突解决"""
        engine = DataFusionEngine()

        source_data_list = [
            SourceData(
                source_id="source_1",
                source_type=DataSourceType.SQL_QUERY,
                content="销售数据：1000",
                confidence=0.9
            ),
            SourceData(
                source_id="source_2",
                source_type=DataSourceType.RAG_RETRIEVAL,
                content="销售数据：800",
                confidence=0.7
            )
        ]

        conflicts = [
            ConflictInfo(
                conflict_type="factual_conflict",
                conflicting_sources=["source_1", "source_2"],
                conflict_description="事实冲突",
                resolution_strategy=ConflictResolutionStrategy.TRUST_HIGHEST_CONFIDENCE,
                resolution_result="pending",
                confidence_impact=0.3
            )
        ]

        resolved_data = await engine._resolve_conflicts(source_data_list, conflicts)

        assert len(resolved_data) == 2
        assert conflicts[0].resolution_result is not None

    @pytest.mark.asyncio
    async def test_quality_assessment(self, sample_sql_results, sample_rag_results):
        """测试答案质量评估"""
        result = await fusion_engine.fuse_multi_source_data(
            query="测试查询",
            sql_results=sample_sql_results,
            rag_results=sample_rag_results,
            tenant_id="test_tenant"
        )

        assert result.answer_quality_score >= 0
        assert result.answer_quality_score <= 1.0

        # 多源数据应该有较高的质量分数
        assert result.answer_quality_score > 0.5

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试无效输入
        result = await fusion_engine.fuse_multi_source_data(
            query="",
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.answer is not None

    def test_data_source_standardization(self, sample_sql_results, sample_rag_results, sample_documents):
        """测试数据源标准化"""
        engine = DataFusionEngine()

        # 运行标准化
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            source_data_list = loop.run_until_complete(
                engine._standardize_input_data(
                    sample_sql_results, sample_rag_results, sample_documents
                )
            )

            assert len(source_data_list) == (
                len(sample_sql_results) + len(sample_rag_results) + len(sample_documents)
            )

            # 检查SQL数据
            sql_sources = [s for s in source_data_list if s.source_type == DataSourceType.SQL_QUERY]
            assert len(sql_sources) == len(sample_sql_results)

            # 检查RAG数据
            rag_sources = [s for s in source_data_list if s.source_type == DataSourceType.RAG_RETRIEVAL]
            assert len(rag_sources) == len(sample_rag_results)

            # 检查文档数据
            doc_sources = [s for s in source_data_list if s.source_type == DataSourceType.DOCUMENT]
            assert len(doc_sources) == len(sample_documents)

        finally:
            loop.close()

    def test_content_cleaning(self):
        """测试内容清洗功能"""
        engine = DataFusionEngine()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 测试正常内容
            normal_content = "这是一个正常的内容。"
            cleaned = loop.run_until_complete(engine._clean_content(normal_content))
            assert cleaned == normal_content

            # 测试包含多余空格的内容
            messy_content = "这   是   一个   测试   内容。"
            cleaned = loop.run_until_complete(engine._clean_content(messy_content))
            assert "  " not in cleaned

            # 测试过长内容的截断
            long_content = "a" * 15000
            cleaned = loop.run_until_complete(engine._clean_content(long_content))
            assert len(cleaned) <= 10003  # 10000 + "..."

        finally:
            loop.close()

    def test_key_information_extraction(self):
        """测试关键信息提取"""
        engine = DataFusionEngine()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            content = "销售数据：2024年第三季度达到1200.5万元，同比增长15%。"
            key_info = loop.run_until_complete(engine._extract_key_information(content))

            assert "numbers" in key_info
            assert "2024" in key_info["numbers"]
            assert "1200.5" in key_info["numbers"]
            assert "15" in key_info["numbers"]

            assert "content_length" in key_info
            assert key_info["content_length"] == len(content)

        finally:
            loop.close()

    @pytest.mark.asyncio
    async def test_fusion_explanation_build(self, sample_sql_results):
        """测试融合解释构建"""
        engine = DataFusionEngine()

        # 标准化数据
        source_data_list = await engine._standardize_input_data(
            sample_sql_results, [], []
        )

        # 预处理数据
        processed_data = await engine._preprocess_data(source_data_list)

        # 构建融合内容
        fused_content = await engine._perform_fusion(processed_data, "测试查询")

        # 构建解释
        explanation_steps = await engine._build_fusion_explanation(
            processed_data, [], fused_content
        )

        assert len(explanation_steps) > 0
        assert any(step.description == "多源数据收集" for step in explanation_steps)
        assert any(step.description == "数据质量评估" for step in explanation_steps)

    @pytest.mark.asyncio
    async def test_source_citation_preparation(self, sample_sql_results):
        """测试源引用准备"""
        engine = DataFusionEngine()

        source_data_list = await engine._standardize_input_data(
            sample_sql_results, [], []
        )

        citations = await engine._prepare_source_citations(source_data_list)

        assert len(citations) == len(sample_sql_results)

        for citation in citations:
            assert "source_id" in citation
            assert "source_type" in citation
            assert "confidence" in citation
            assert "timestamp" in citation

    @pytest.mark.asyncio
    async def test_fusion_performance(self, sample_sql_results, sample_rag_results):
        """测试融合性能"""
        start_time = datetime.utcnow()

        result = await fusion_engine.fuse_multi_source_data(
            query="性能测试查询",
            sql_results=sample_sql_results,
            rag_results=sample_rag_results,
            tenant_id="test_tenant"
        )

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # 验证处理时间（应该在合理范围内）
        assert processing_time < 10.0  # 应该在10秒内完成
        assert result.processing_time > 0

        # 验证结果质量
        assert result.answer_quality_score > 0.3

    @pytest.mark.asyncio
    async def test_multilingual_content(self):
        """测试多语言内容处理"""
        query = "What is the sales data?"
        rag_results = [
            {
                "content": "The sales data shows Q3 revenue of $145,000.",
                "similarity_score": 0.9,
                "collection": "english_reports",
                "chunk_id": "chunk_001",
                "document_id": "doc_001",
                "confidence": 0.88
            }
        ]

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            rag_results=rag_results,
            tenant_id="test_tenant"
        )

        assert result is not None
        assert result.answer is not None
        assert len(result.sources) > 0


class TestFusionEngineIntegration:
    """融合引擎集成测试"""

    @pytest.mark.asyncio
    async def test_real_world_scenario(self):
        """测试真实世界场景"""
        query = "分析我们公司第三季度的整体表现，包括销售数据和市场趋势。"

        sql_results = [
            {
                "data": [
                    {"month": "July", "revenue": 45000, "growth": 0.12},
                    {"month": "August", "revenue": 52000, "growth": 0.15},
                    {"month": "September", "revenue": 48000, "growth": 0.08}
                ],
                "query": "SELECT month, revenue, growth FROM quarterly_performance WHERE quarter = 'Q3'",
                "confidence": 0.92,
                "database": "company_db"
            }
        ]

        rag_results = [
            {
                "content": "根据市场分析报告，第三季度行业整体增长平稳，公司在竞争中的表现良好。市场份额有所提升。",
                "similarity_score": 0.88,
                "collection": "market_analysis",
                "chunk_id": "chunk_101",
                "document_id": "market_report_Q3",
                "confidence": 0.85
            },
            {
                "content": "公司Q3季度报告显示，主要产品线的销售表现超出预期，客户满意度保持在较高水平。",
                "similarity_score": 0.91,
                "collection": "company_reports",
                "chunk_id": "chunk_202",
                "document_id": "Q3_summary",
                "confidence": 0.89
            }
        ]

        documents = [
            {
                "title": "2024年第三季度竞争对手分析",
                "content": "主要竞争对手在Q3的表现如下：竞争对手A增长10%，竞争对手B下降5%。我们的相对表现较好。",
                "file_name": "competitor_analysis_Q3.pdf",
                "file_type": "pdf",
                "section": "summary",
                "confidence": 0.80
            }
        ]

        result = await fusion_engine.fuse_multi_source_data(
            query=query,
            sql_results=sql_results,
            rag_results=rag_results,
            documents=documents,
            tenant_id="integration_test"
        )

        # 验证结果
        assert result is not None
        assert len(result.answer) > 100  # 应该是一个详细的答案
        assert result.confidence > 0.7  # 应该有较高的置信度
        assert result.answer_quality_score > 0.6  # 应该有较好的质量
        assert len(result.sources) >= 3  # 应该引用多个数据源

        # 验证融合元数据
        assert result.fusion_metadata["source_count"] >= 3
        assert "processing_timestamp" in result.fusion_metadata

    @pytest.mark.asyncio
    async def test_edge_cases(self):
        """测试边界情况"""
        # 测试单字符查询
        result1 = await fusion_engine.fuse_multi_source_data(
            query="a",
            tenant_id="test_tenant"
        )
        assert result1 is not None

        # 测试超长查询
        long_query = "测试" * 1000
        result2 = await fusion_engine.fuse_multi_source_data(
            query=long_query,
            tenant_id="test_tenant"
        )
        assert result2 is not None

        # 测试特殊字符查询
        special_query = "测试查询 @#$%^&*()_+{}|:<>?[]\\;'\",./"
        result3 = await fusion_engine.fuse_multi_source_data(
            query=special_query,
            tenant_id="test_tenant"
        )
        assert result3 is not None