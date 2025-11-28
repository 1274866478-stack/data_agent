"""
Unit tests for RAG services
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from src.services.rag_document_processor import DocumentProcessor
from src.services.embedding_service import EmbeddingService
from src.services.retrieval_service import RetrievalService, SearchConfig
from src.services.rag_service import RAGService
from src.models.rag_models import (
    DocumentChunk,
    VectorCollection,
    RetrievalResult,
    RAGQueryRequest,
    RetrievalMode,
    ChunkingStrategy
)


class TestDocumentProcessor:
    """Test cases for DocumentProcessor"""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    @pytest.mark.asyncio
    async def test_validate_document_success(self, processor):
        """Test successful document validation"""
        file_content = b"Test document content"
        file_name = "test.txt"
        file_type = "txt"

        # Should not raise exception
        await processor._validate_document(file_content, file_name, file_type)

    @pytest.mark.asyncio
    async def test_validate_document_invalid_size(self, processor):
        """Test document validation with oversized file"""
        file_content = b"x" * (100 * 1024 * 1024)  # 100MB
        file_name = "large.txt"
        file_type = "txt"

        with pytest.raises(ValueError, match="文件大小超过限制"):
            await processor._validate_document(file_content, file_name, file_type)

    @pytest.mark.asyncio
    async def test_validate_document_invalid_type(self, processor):
        """Test document validation with unsupported file type"""
        file_content = b"Test content"
        file_name = "test.xyz"
        file_type = "xyz"

        with pytest.raises(ValueError, match="不支持的文件类型"):
            await processor._validate_document(file_content, file_name, file_type)

    @pytest.mark.asyncio
    async def test_extract_txt_text(self, processor):
        """Test text extraction from TXT file"""
        file_content = "This is a test document.\nWith multiple lines."
        expected_text = "This is a test document.\nWith multiple lines."

        text, metadata = await processor._extract_txt_text(file_content, "test.txt")

        assert text == expected_text
        assert metadata['extraction_method'] == 'utf-8-decode'
        assert metadata['character_count'] == len(expected_text)

    @pytest.mark.asyncio
    async def test_clean_text(self, processor):
        """Test text cleaning functionality"""
        dirty_text = "  This    is   a   test  \n\n  document  with   extra   spaces.  "
        expected_text = "This is a test document with extra spaces."

        cleaned = await processor._clean_text(dirty_text)

        assert cleaned == expected_text

    def test_estimate_tokens(self, processor):
        """Test token estimation"""
        english_text = "This is a test with English words."
        chinese_text = "这是一个中文测试文本。"

        english_tokens = processor._estimate_tokens(english_text)
        chinese_tokens = processor._estimate_tokens(chinese_text)

        assert english_tokens > 0
        assert chinese_tokens > 0
        assert english_tokens != chinese_tokens

    @pytest.mark.asyncio
    async def test_create_document_chunk(self, processor):
        """Test document chunk creation"""
        content = "This is a test chunk content."
        chunk = await processor._create_document_chunk(
            content=content,
            chunk_index=0,
            document_id=1,
            tenant_id="test-tenant",
            collection_id="test-collection",
            file_name="test.txt",
            file_type="txt",
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=512,
            overlap_size=0,
            metadata={}
        )

        assert chunk.content == content
        assert chunk.chunk_index == 0
        assert chunk.document_id == 1
        assert chunk.tenant_id == "test-tenant"
        assert chunk.chunking_strategy == ChunkingStrategy.SEMANTIC
        assert chunk.content_length == len(content)


class TestEmbeddingService:
    """Test cases for EmbeddingService"""

    @pytest.fixture
    def service(self):
        return EmbeddingService()

    @pytest.mark.asyncio
    async def test_get_content_hash(self, service):
        """Test content hash generation"""
        content = "Test content for hashing"
        hash1 = service._get_content_hash(content)
        hash2 = service._get_content_hash(content)
        hash3 = service._get_content_hash("Different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex length

    def test_estimate_tokens(self, service):
        """Test token estimation"""
        text = "This is a test sentence for token estimation."
        tokens = service._estimate_tokens(text)

        assert tokens > 0
        assert isinstance(tokens, int)

    @pytest.mark.asyncio
    async def test_validate_embedding_quality(self, service):
        """Test embedding quality validation"""
        # Valid embedding
        valid_embedding = [0.1, -0.2, 0.3, 0.4] * 256  # 1024 dimensions
        text = "Test text for embedding"

        result = await service.validate_embedding_quality(valid_embedding, text)

        assert result['is_valid'] is True
        assert 'metrics' in result
        assert 'norm' in result['metrics']

        # Invalid embedding (wrong dimension)
        invalid_embedding = [0.1, 0.2, 0.3]  # Too short
        result = await service.validate_embedding_quality(invalid_embedding, text)

        assert result['is_valid'] is False
        assert len(result['issues']) > 0

    @pytest.mark.asyncio
    async def test_update_stats(self, service):
        """Test statistics updates"""
        initial_stats = await service.get_statistics()
        initial_count = initial_stats['total_embeddings_generated']

        service._update_stats(tokens_processed=100, processing_time_ms=500)

        updated_stats = await service.get_statistics()
        assert updated_stats['total_embeddings_generated'] == initial_count + 1
        assert updated_stats['total_tokens_processed'] == 100
        assert updated_stats['total_processing_time_ms'] == 500


class TestRetrievalService:
    """Test cases for RetrievalService"""

    @pytest.fixture
    def service(self):
        return RetrievalService()

    @pytest.fixture
    def search_config(self):
        return SearchConfig(
            max_results=5,
            similarity_threshold=0.7,
            context_max_tokens=1000
        )

    def test_extract_keywords(self, service):
        """Test keyword extraction"""
        query = "How to process documents with semantic chunking?"
        keywords = service._extract_keywords(query)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "the" not in keywords  # Stop words should be removed
        assert "process" in keywords or "documents" in keywords

    def test_calculate_content_similarity(self, service):
        """Test content similarity calculation"""
        text1 = "This is about document processing"
        text2 = "This is about document processing and analysis"
        text3 = "Completely different topic about cooking"

        similarity_1_2 = service._calculate_content_similarity(text1, text2)
        similarity_1_3 = service._calculate_content_similarity(text1, text3)

        assert 0 <= similarity_1_2 <= 1
        assert 0 <= similarity_1_3 <= 1
        assert similarity_1_2 > similarity_1_3  # More similar texts should have higher score

    def test_estimate_tokens(self, service):
        """Test token estimation"""
        text = "This is a test with multiple words for token estimation."
        tokens = service._estimate_tokens(text)

        assert tokens > 0
        assert isinstance(tokens, float)

    @pytest.mark.asyncio
    async def test_build_context(self, service):
        """Test context building from results"""
        results = [
            RetrievalResult(
                chunk_id="1",
                content="First chunk content with important information.",
                content_preview="First chunk content...",
                document_id=1,
                document_title="Doc 1",
                file_name="doc1.txt",
                file_type="txt",
                similarity_score=0.9,
                rank=1,
                content_length=50,
                token_count=12,
                chunk_index=0
            ),
            RetrievalResult(
                chunk_id="2",
                content="Second chunk content with additional details.",
                content_preview="Second chunk content...",
                document_id=2,
                document_title="Doc 2",
                file_name="doc2.txt",
                file_type="txt",
                similarity_score=0.8,
                rank=2,
                content_length=45,
                token_count=10,
                chunk_index=0
            )
        ]

        context, sources, metadata = await service.build_context(
            results,
            max_tokens=50,
            include_metadata=True
        )

        assert len(context) > 0
        assert len(sources) == 1  # Only first result fits within token limit
        assert metadata['total_tokens'] <= 50
        assert metadata['sources_used'] == len(sources)
        assert "doc1.txt" in context

    def test_update_stats(self, service):
        """Test statistics updates"""
        initial_stats = service.stats.copy()

        service._update_stats(result_count=5, processing_time_ms=1000)

        assert service.stats['total_queries'] == initial_stats['total_queries'] + 1
        assert service.stats['total_retrievals'] == initial_stats['total_retrievals'] + 5
        assert service.stats['average_query_time_ms'] > 0


class TestRAGService:
    """Test cases for RAGService"""

    @pytest.fixture
    def service(self):
        return RAGService()

    @pytest.fixture
    def sample_request(self):
        return RAGQueryRequest(
            query="What is document processing?",
            tenant_id="test-tenant",
            session_id=None,
            retrieval_mode=RetrievalMode.SEMANTIC,
            max_results=5,
            similarity_threshold=0.7,
            collections=[],
            max_context_tokens=1000,
            include_metadata=True,
            generate_answer=True,
            answer_style="concise",
            temperature=0.3
        )

    def test_generate_query_understanding(self, service):
        """Test query understanding generation"""
        query = "How to process PDF documents?"
        results = [
            RetrievalResult(
                chunk_id="1",
                content="PDF processing requires text extraction",
                content_preview="PDF processing...",
                document_id=1,
                document_title="PDF Guide",
                file_name="pdf_guide.pdf",
                file_type="pdf",
                similarity_score=0.9,
                rank=1,
                content_length=40,
                token_count=8,
                chunk_index=0
            )
        ]

        understanding = service._generate_query_understanding(query, results)

        assert query in understanding
        assert "1个相关文档" in understanding or "1个相关文档" in understanding
        assert "0.90" in understanding

    @pytest.mark.asyncio
    async def test_get_tenant_collections_empty(self, service):
        """Test getting tenant collections when none specified"""
        collections = await service._get_tenant_collections("test-tenant", [])

        assert len(collections) == 1
        assert collections[0].name == "documents"
        assert collections[0].tenant_id == "test-tenant"

    @pytest.mark.asyncio
    async def test_get_tenant_collections_with_ids(self, service):
        """Test getting tenant collections with specific IDs"""
        collection_ids = ["collection1", "collection2"]
        collections = await service._get_tenant_collections("test-tenant", collection_ids)

        assert len(collections) == 2
        assert collections[0].id == "collection1"
        assert collections[1].id == "collection2"
        assert all(c.tenant_id == "test-tenant" for c in collections)

    def test_update_global_stats(self, service):
        """Test global statistics updates"""
        initial_stats = service.stats.copy()

        # Update successful query
        service._update_global_stats(True, 1500)

        assert service.stats['total_queries_processed'] == initial_stats['total_queries_processed'] + 1
        assert service.stats['successful_queries'] == initial_stats['successful_queries'] + 1
        assert service.stats['average_response_time_ms'] > 0

        # Update failed query
        service._update_global_stats(False, 500)

        assert service.stats['total_queries_processed'] == initial_stats['total_queries_processed'] + 2
        assert service.stats['failed_queries'] == initial_stats['failed_queries'] + 1

    def test_update_satisfaction_stats(self, service):
        """Test satisfaction statistics updates"""
        initial_avg = service.stats['user_satisfaction_average']
        initial_count = service.stats['successful_queries'] if initial_avg > 0 else 0

        # Add feedback
        service._update_satisfaction_stats(5)  # Perfect rating

        new_avg = service.stats['user_satisfaction_average']
        assert new_avg > initial_avg if initial_avg > 0 else new_avg == 5

    @pytest.mark.asyncio
    async def test_get_collection_by_id(self, service):
        """Test getting collection by ID"""
        collection = await service._get_collection_by_id("test-collection", "test-tenant")

        assert collection is not None
        assert collection.id == "test-collection"
        assert collection.tenant_id == "test-tenant"
        assert collection.name == "documents"


class TestRAGIntegration:
    """Integration tests for RAG services"""

    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test full RAG pipeline with mocked dependencies"""
        # This would be a more comprehensive integration test
        # For now, we'll test the basic flow structure

        # Mock the dependencies
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding:
            with patch('src.services.rag_service.RetrievalService') as MockRetrieval:
                with patch('src.services.rag_service.ZhipuService') as MockZhipu:

                    # Setup mocks
                    mock_embedding_service = AsyncMock()
                    mock_retrieval_service = AsyncMock()
                    mock_zhipu_service = AsyncMock()

                    MockEmbedding.return_value = mock_embedding_service
                    MockRetrieval.return_value = mock_retrieval_service
                    MockZhipu.return_value = mock_zhipu_service

                    # Configure mock responses
                    mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 100})
                    mock_retrieval_service.retrieve_documents.return_value = ([], {"processing_time_ms": 200})
                    mock_retrieval_service.build_context.return_value = ("", [], {"total_tokens": 0})
                    mock_zhipu_service.chat_completion.return_value = "Test answer"

                    # Create service and test
                    service = RAGService()
                    request = RAGQueryRequest(
                        query="Test query",
                        tenant_id="test-tenant",
                        generate_answer=False  # Skip LLM for simpler test
                    )

                    response = await service.process_query(request)

                    assert response is not None
                    assert response.query == "Test query"
                    assert response.tenant_id == "test-tenant"


class TestRAGLLMIntegration:
    """RAG与LLM集成测试"""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline_with_llm_answer(self):
        """测试完整RAG管道（含LLM答案生成）"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            # 设置Mock服务
            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            # 配置嵌入服务Mock
            mock_embedding_service.generate_embedding.return_value = (
                [0.1] * 1024,
                {"processing_time_ms": 50}
            )

            # 配置检索结果Mock
            mock_retrieval_results = [
                RetrievalResult(
                    chunk_id="chunk_1",
                    content="机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习。",
                    content_preview="机器学习是人工智能...",
                    document_id=1,
                    document_title="AI基础",
                    file_name="ai_basics.pdf",
                    file_type="pdf",
                    similarity_score=0.92,
                    rank=1,
                    content_length=40,
                    token_count=20,
                    chunk_index=0
                ),
                RetrievalResult(
                    chunk_id="chunk_2",
                    content="深度学习是机器学习的子集，使用神经网络进行特征学习。",
                    content_preview="深度学习是机器学习...",
                    document_id=2,
                    document_title="深度学习入门",
                    file_name="deep_learning.pdf",
                    file_type="pdf",
                    similarity_score=0.85,
                    rank=2,
                    content_length=35,
                    token_count=18,
                    chunk_index=0
                )
            ]

            mock_retrieval_service.retrieve_documents.return_value = (
                mock_retrieval_results,
                {"processing_time_ms": 100}
            )

            # 配置上下文构建Mock
            context_text = """
            [来源: ai_basics.pdf]
            机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习。

            [来源: deep_learning.pdf]
            深度学习是机器学习的子集，使用神经网络进行特征学习。
            """
            mock_retrieval_service.build_context.return_value = (
                context_text,
                ["ai_basics.pdf", "deep_learning.pdf"],
                {"total_tokens": 50}
            )

            # 配置LLM响应Mock
            mock_zhipu_service.chat_completion.return_value = (
                "机器学习是人工智能的重要分支，它让计算机能够从数据中自动学习和改进。"
                "深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的复杂特征表示。"
            )

            # 创建服务并测试
            service = RAGService()
            request = RAGQueryRequest(
                query="什么是机器学习和深度学习？",
                tenant_id="test-tenant",
                generate_answer=True,
                answer_style="detailed",
                temperature=0.3
            )

            response = await service.process_query(request)

            # 验证响应
            assert response is not None
            assert response.success is True
            assert response.query == "什么是机器学习和深度学习？"
            assert response.tenant_id == "test-tenant"
            assert response.total_retrieved == 2
            assert response.answer is not None
            assert "机器学习" in response.answer
            assert response.answer_confidence > 0.8  # 高置信度

    @pytest.mark.asyncio
    async def test_rag_with_different_answer_styles(self):
        """测试不同答案风格的RAG"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            # 基础Mock配置
            mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 50})

            mock_retrieval_results = [
                RetrievalResult(
                    chunk_id="chunk_1",
                    content="人工智能基础知识",
                    content_preview="人工智能基础...",
                    document_id=1,
                    document_title="AI入门",
                    file_name="ai_intro.pdf",
                    file_type="pdf",
                    similarity_score=0.9,
                    rank=1,
                    content_length=20,
                    token_count=10,
                    chunk_index=0
                )
            ]
            mock_retrieval_service.retrieve_documents.return_value = (mock_retrieval_results, {"processing_time_ms": 50})
            mock_retrieval_service.build_context.return_value = ("AI基础知识", ["ai_intro.pdf"], {"total_tokens": 20})

            answer_styles = ["concise", "detailed", "creative"]
            expected_responses = {
                "concise": "AI是模拟人类智能的技术。",
                "detailed": "人工智能是一个广泛的计算机科学领域，专注于创建能够执行通常需要人类智能的任务的系统...",
                "creative": "想象一下，如果计算机能够像人类一样思考、学习和创造..."
            }

            for style in answer_styles:
                mock_zhipu_service.chat_completion.return_value = expected_responses[style]

                service = RAGService()
                request = RAGQueryRequest(
                    query="什么是AI？",
                    tenant_id="test-tenant",
                    generate_answer=True,
                    answer_style=style,
                    temperature=0.3 if style == "concise" else 0.7
                )

                response = await service.process_query(request)

                assert response is not None
                assert response.answer is not None


class TestChromaDBZhipuIntegration:
    """ChromaDB与智谱AI协同测试"""

    @pytest.mark.asyncio
    async def test_chromadb_retrieval_to_zhipu_answer(self):
        """测试ChromaDB检索到智谱AI回答的完整流程"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            # 模拟ChromaDB返回的结果
            mock_embedding_service.generate_embedding.return_value = ([0.15] * 1024, {"processing_time_ms": 30})

            chromadb_mock_results = [
                RetrievalResult(
                    chunk_id="chroma_doc_1",
                    content="PostgreSQL是一个功能强大的开源对象关系数据库系统。",
                    content_preview="PostgreSQL是一个...",
                    document_id=1,
                    document_title="数据库指南",
                    file_name="db_guide.pdf",
                    file_type="pdf",
                    similarity_score=0.88,
                    rank=1,
                    content_length=30,
                    token_count=15,
                    chunk_index=0
                )
            ]

            mock_retrieval_service.retrieve_documents.return_value = (chromadb_mock_results, {"processing_time_ms": 80})
            mock_retrieval_service.build_context.return_value = (
                "[来源: db_guide.pdf]\nPostgreSQL是一个功能强大的开源对象关系数据库系统。",
                ["db_guide.pdf"],
                {"total_tokens": 25}
            )

            # 智谱AI基于检索内容生成回答
            mock_zhipu_service.chat_completion.return_value = (
                "PostgreSQL是一个功能强大的开源对象关系数据库管理系统(ORDBMS)，"
                "它以其可靠性、数据完整性和正确性著称，支持复杂查询和事务处理。"
            )

            service = RAGService()
            request = RAGQueryRequest(
                query="什么是PostgreSQL？",
                tenant_id="test-tenant",
                generate_answer=True
            )

            response = await service.process_query(request)

            assert response.success is True
            assert response.total_retrieved == 1
            assert "PostgreSQL" in response.answer
            assert response.context_length > 0

    @pytest.mark.asyncio
    async def test_empty_chromadb_results_handling(self):
        """测试ChromaDB无结果时的处理"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 30})
            mock_retrieval_service.retrieve_documents.return_value = ([], {"processing_time_ms": 50})
            mock_retrieval_service.build_context.return_value = ("", [], {"total_tokens": 0})

            service = RAGService()
            request = RAGQueryRequest(
                query="这是一个找不到相关文档的查询",
                tenant_id="test-tenant",
                generate_answer=True
            )

            response = await service.process_query(request)

            assert response.success is True
            assert response.total_retrieved == 0
            # 无检索结果时，answer可能为None或提示信息
            assert response.context_length == 0


class TestKnowledgeBaseQA:
    """知识库问答场景测试"""

    @pytest.mark.asyncio
    async def test_multi_document_qa(self):
        """测试多文档问答"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 30})

            # 模拟来自多个文档的检索结果
            multi_doc_results = [
                RetrievalResult(
                    chunk_id=f"doc_{i}_chunk",
                    content=f"文档{i}的相关内容：这是关于主题的第{i}个观点。",
                    content_preview=f"文档{i}的相关内容...",
                    document_id=i,
                    document_title=f"文档{i}",
                    file_name=f"document_{i}.pdf",
                    file_type="pdf",
                    similarity_score=0.9 - i * 0.1,
                    rank=i,
                    content_length=30,
                    token_count=15,
                    chunk_index=0
                )
                for i in range(1, 4)
            ]

            mock_retrieval_service.retrieve_documents.return_value = (multi_doc_results, {"processing_time_ms": 100})
            mock_retrieval_service.build_context.return_value = (
                "综合多个文档的内容...",
                ["document_1.pdf", "document_2.pdf", "document_3.pdf"],
                {"total_tokens": 60}
            )
            mock_zhipu_service.chat_completion.return_value = "综合三个文档的观点，我们可以得出..."

            service = RAGService()
            request = RAGQueryRequest(
                query="综合多个文档的信息回答问题",
                tenant_id="test-tenant",
                max_results=5,
                generate_answer=True
            )

            response = await service.process_query(request)

            assert response.success is True
            assert response.total_retrieved == 3
            assert response.answer is not None
            assert len(response.context_used) == 3

    @pytest.mark.asyncio
    async def test_qa_with_source_citation(self):
        """测试带来源引用的问答"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 30})

            source_results = [
                RetrievalResult(
                    chunk_id="policy_chunk",
                    content="公司政策规定：员工每年享有15天带薪年假。",
                    content_preview="公司政策规定...",
                    document_id=1,
                    document_title="员工手册",
                    file_name="employee_handbook.pdf",
                    file_type="pdf",
                    similarity_score=0.95,
                    rank=1,
                    content_length=25,
                    token_count=12,
                    chunk_index=5
                )
            ]

            mock_retrieval_service.retrieve_documents.return_value = (source_results, {"processing_time_ms": 50})
            mock_retrieval_service.build_context.return_value = (
                "[来源: 员工手册, 第5章]\n公司政策规定：员工每年享有15天带薪年假。",
                ["employee_handbook.pdf"],
                {"total_tokens": 20}
            )
            mock_zhipu_service.chat_completion.return_value = (
                "根据《员工手册》规定，员工每年享有15天带薪年假。[来源: employee_handbook.pdf]"
            )

            service = RAGService()
            request = RAGQueryRequest(
                query="员工有多少天年假？",
                tenant_id="test-tenant",
                generate_answer=True,
                include_metadata=True
            )

            response = await service.process_query(request)

            assert response.success is True
            assert "15天" in response.answer or "15" in response.answer


class TestRAGReasoningIntegration:
    """RAG与推理服务集成测试"""

    @pytest.mark.asyncio
    async def test_rag_with_reasoning_steps(self):
        """测试带推理步骤的RAG"""
        with patch('src.services.rag_service.EmbeddingService') as MockEmbedding, \
             patch('src.services.rag_service.RetrievalService') as MockRetrieval, \
             patch('src.services.rag_service.ZhipuService') as MockZhipu:

            mock_embedding_service = AsyncMock()
            mock_retrieval_service = AsyncMock()
            mock_zhipu_service = AsyncMock()

            MockEmbedding.return_value = mock_embedding_service
            MockRetrieval.return_value = mock_retrieval_service
            MockZhipu.return_value = mock_zhipu_service

            mock_embedding_service.generate_embedding.return_value = ([0.1] * 1024, {"processing_time_ms": 30})

            reasoning_results = [
                RetrievalResult(
                    chunk_id="fact_1",
                    content="销售额在Q1增长了15%。",
                    content_preview="销售额在Q1...",
                    document_id=1,
                    document_title="Q1报告",
                    file_name="q1_report.pdf",
                    file_type="pdf",
                    similarity_score=0.9,
                    rank=1,
                    content_length=15,
                    token_count=8,
                    chunk_index=0
                ),
                RetrievalResult(
                    chunk_id="fact_2",
                    content="Q2销售额继续增长10%。",
                    content_preview="Q2销售额继续...",
                    document_id=2,
                    document_title="Q2报告",
                    file_name="q2_report.pdf",
                    file_type="pdf",
                    similarity_score=0.85,
                    rank=2,
                    content_length=15,
                    token_count=8,
                    chunk_index=0
                )
            ]

            mock_retrieval_service.retrieve_documents.return_value = (reasoning_results, {"processing_time_ms": 60})
            mock_retrieval_service.build_context.return_value = (
                "Q1销售额增长15%，Q2继续增长10%。",
                ["q1_report.pdf", "q2_report.pdf"],
                {"total_tokens": 30}
            )

            # 模拟包含推理过程的回答
            mock_zhipu_service.chat_completion.return_value = (
                "基于报告数据分析：\n"
                "1. Q1销售额增长15%\n"
                "2. Q2销售额继续增长10%\n"
                "结论：上半年销售呈持续增长态势，累计增长约26.5%。"
            )

            service = RAGService()
            request = RAGQueryRequest(
                query="分析上半年销售趋势",
                tenant_id="test-tenant",
                generate_answer=True,
                answer_style="detailed"
            )

            response = await service.process_query(request)

            assert response.success is True
            assert response.answer is not None
            assert "增长" in response.answer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])