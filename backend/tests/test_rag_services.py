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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])