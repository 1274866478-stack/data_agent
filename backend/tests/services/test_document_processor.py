"""
文档处理器单元测试 - Story 2.4规范验证
测试文档处理服务的核心功能、文件解析和状态更新
"""

import pytest
import uuid
import io
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.app.services.document_processor import DocumentProcessor
from src.app.data.models import KnowledgeDocument, DocumentStatus, Tenant


class TestDocumentProcessor:
    """文档处理器测试类"""

    @pytest.fixture
    def document_processor(self):
        """创建文档处理器实例"""
        return DocumentProcessor()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
        session.rollback = Mock()
        session.query = Mock()
        session.filter = Mock()
        session.filter_by = Mock()
        session.first = Mock()
        return session

    @pytest.fixture
    def mock_document(self):
        """模拟文档对象"""
        document = Mock(spec=KnowledgeDocument)
        document.id = uuid.uuid4()
        document.tenant_id = "test-tenant-123"
        document.file_name = "test.pdf"
        document.storage_path = "dataagent-docs/tenant-test-tenant-123/documents/test.pdf"
        document.file_type = "pdf"
        document.file_size = 1024 * 1024  # 1MB
        document.mime_type = "application/pdf"
        document.status = DocumentStatus.PENDING
        document.processing_error = None
        document.indexed_at = None
        document.created_at = datetime.now(timezone.utc)
        document.updated_at = datetime.now(timezone.utc)

        return document

    @pytest.fixture
    def sample_pdf_data(self):
        """模拟PDF文件数据"""
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"

    @pytest.fixture
    def sample_docx_data(self):
        """模拟DOCX文件数据（ZIP格式）"""
        return b"PK\x03\x04\x14\x00\x06\x00"  # 简化的ZIP文件头

    def test_validate_pdf_integrity_success(self, document_processor, sample_pdf_data):
        """测试PDF文件完整性验证 - 成功"""
        result = document_processor._validate_pdf_integrity(sample_pdf_data)
        assert result["valid"] is True

    def test_validate_pdf_integrity_failure(self, document_processor):
        """测试PDF文件完整性验证 - 失败"""
        invalid_pdf_data = b"NOT_A_PDF_FILE"
        result = document_processor._validate_pdf_integrity(invalid_pdf_data)
        assert result["valid"] is False
        assert "不是有效的PDF格式" in result["error"]

    def test_validate_docx_integrity_success(self, document_processor, sample_docx_data):
        """测试DOCX文件完整性验证 - 成功"""
        result = document_processor._validate_docx_integrity(sample_docx_data)
        assert result["valid"] is True

    def test_validate_docx_integrity_failure(self, document_processor):
        """测试DOCX文件完整性验证 - 失败"""
        invalid_docx_data = b"NOT_A_DOCX_FILE"
        result = document_processor._validate_docx_integrity(invalid_docx_data)
        assert result["valid"] is False
        assert "不是有效的DOCX格式" in result["error"]

    @patch('src.app.services.document_processor.minio_service')
    def test_validate_file_integrity_pdf_success(self, mock_minio, document_processor, mock_document, sample_pdf_data):
        """测试文件完整性验证 - PDF成功"""
        # 设置模拟
        mock_minio.download_file.return_value = sample_pdf_data

        # 执行验证
        result = document_processor._validate_file_integrity(mock_document)

        # 验证结果
        assert result["valid"] is True

    @patch('src.app.services.document_processor.minio_service')
    def test_validate_file_integrity_minio_failure(self, mock_minio, document_processor, mock_document):
        """测试文件完整性验证 - MinIO失败"""
        # 设置模拟
        mock_minio.download_file.return_value = None

        # 执行验证
        result = document_processor._validate_file_integrity(mock_document)

        # 验证结果
        assert result["valid"] is False
        assert "不存在或无法访问" in result["error"]

    @patch('src.app.services.document_processor.minio_service')
    def test_validate_file_integrity_size_mismatch(self, mock_minio, document_processor, mock_document):
        """测试文件完整性验证 - 文件大小不匹配"""
        # 设置模拟 - 返回的文件大小与记录不符
        mock_minio.download_file.return_value = b"small_file"

        # 执行验证
        result = document_processor._validate_file_integrity(mock_document)

        # 验证结果
        assert result["valid"] is False
        assert "文件大小不匹配" in result["error"]

    @patch('src.app.services.document_processor.minio_service')
    def test_extract_text_from_pdf_success(self, mock_minio, document_processor, mock_document, sample_pdf_data):
        """测试从PDF提取文本成功"""
        # 设置模拟
        mock_minio.download_file.return_value = sample_pdf_data

        # 执行文本提取
        result = document_processor._extract_text_from_document(mock_document)

        # 验证结果
        assert result["success"] is True
        assert "text" in result
        assert "metadata" in result
        assert "PDF文档内容" in result["text"]

    @patch('src.app.services.document_processor.minio_service')
    def test_extract_text_from_docx_success(self, mock_minio, document_processor, mock_document, sample_docx_data):
        """测试从DOCX提取文本成功"""
        # 设置文档类型为DOCX
        mock_document.file_type = "docx"
        mock_minio.download_file.return_value = sample_docx_data

        # 执行文本提取
        result = document_processor._extract_text_from_document(mock_document)

        # 验证结果
        assert result["success"] is True
        assert "text" in result
        assert "metadata" in result
        assert "DOCX文档内容" in result["text"]

    @patch('src.app.services.document_processor.minio_service')
    def test_extract_text_minio_failure(self, mock_minio, document_processor, mock_document):
        """测试文本提取 - MinIO失败"""
        # 设置模拟
        mock_minio.download_file.return_value = None

        # 执行文本提取
        result = document_processor._extract_text_from_document(mock_document)

        # 验证结果
        assert result["success"] is False
        assert "无法从MinIO获取文件" in result["error"]

    def test_process_document_metadata(self, document_processor, mock_document):
        """测试处理文档元数据"""
        extracted_text = "This is a sample document text content."
        file_metadata = {
            "title": "Sample Document",
            "author": "Test Author"
        }

        # 执行元数据处理
        result = document_processor._process_document_metadata(mock_document, extracted_text, file_metadata)

        # 验证结果
        assert "file_info" in result
        assert "extraction_metadata" in result
        assert "text_analysis" in result
        assert "processing_info" in result

        # 验证文件信息
        assert result["file_info"]["file_name"] == mock_document.file_name
        assert result["file_info"]["file_type"] == mock_document.file_type
        assert result["file_info"]["file_size"] == mock_document.file_size

        # 验证文本分析
        assert result["text_analysis"]["character_count"] == len(extracted_text)
        assert result["text_analysis"]["word_count"] == len(extracted_text.split())

    def test_prepare_for_vectorization(self, document_processor, mock_document):
        """测试准备向量化"""
        extracted_text = "This is a sample document text content for vectorization testing."

        # 执行向量化准备
        result = document_processor._prepare_for_vectorization(mock_document, extracted_text)

        # 验证结果
        assert "status" in result
        assert "text_chunks_count" in result
        assert "total_characters" in result
        assert "estimated_tokens" in result
        assert "collection_name" in result

        assert result["status"] == "ready_for_vectorization"
        assert result["collection_name"] == f"tenant_{mock_document.tenant_id}_docs"

    def test_split_text_into_chunks(self, document_processor):
        """测试文本分割"""
        text = "This is a long text that should be split into multiple chunks for processing. " * 20

        # 执行文本分割
        chunks = document_processor._split_text_into_chunks(text, chunk_size=100, overlap=20)

        # 验证结果
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)

    def test_split_text_into_chunks_short_text(self, document_processor):
        """测试文本分割 - 短文本"""
        text = "This is a short text."

        # 执行文本分割
        chunks = document_processor._split_text_into_chunks(text, chunk_size=100, overlap=20)

        # 验证结果
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0] == text

    @patch('src.app.services.document_processor.minio_service')
    def test_process_document_async_success(self, mock_minio, document_processor, mock_db_session, mock_document, sample_pdf_data):
        """测试异步文档处理成功"""
        # 设置模拟
        mock_minio.download_file.return_value = sample_pdf_data

        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行文档处理
        result = document_processor.process_document_async(
            db=mock_db_session,
            tenant_id=mock_document.tenant_id,
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is True
        assert "processing_result" in result
        assert result["document_id"] == str(mock_document.id)

    def test_process_document_async_document_not_found(self, document_processor, mock_db_session):
        """测试异步文档处理 - 文档不存在"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # 执行文档处理
        result = document_processor.process_document_async(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=uuid.uuid4()
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "DOCUMENT_NOT_FOUND"

    def test_process_document_async_already_processed(self, document_processor, mock_db_session, mock_document):
        """测试异步文档处理 - 文档已处理"""
        # 设置文档状态为READY
        mock_document.status = DocumentStatus.READY

        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行文档处理
        result = document_processor.process_document_async(
            db=mock_db_session,
            tenant_id=mock_document.tenant_id,
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "DOCUMENT_ALREADY_PROCESSED"

    def test_get_processing_status_success(self, document_processor, mock_db_session, mock_document):
        """测试获取处理状态成功"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行状态查询
        result = document_processor.get_processing_status(
            db=mock_db_session,
            tenant_id=mock_document.tenant_id,
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is True
        assert "document_id" in result
        assert "status" in result
        assert result["document_id"] == str(mock_document.id)
        assert result["status"] == mock_document.status.value

    def test_get_processing_status_not_found(self, document_processor, mock_db_session):
        """测试获取处理状态 - 文档不存在"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # 执行状态查询
        result = document_processor.get_processing_status(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=uuid.uuid4()
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "DOCUMENT_NOT_FOUND"

    @patch.object(DocumentProcessor, 'process_document_async')
    def test_batch_process_documents_success(self, mock_process_async, document_processor, mock_db_session):
        """测试批量处理文档成功"""
        # 设置模拟
        document_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        mock_process_async.return_value = {"success": True}

        # 执行批量处理
        result = document_processor.batch_process_documents(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_ids=document_ids
        )

        # 验证结果
        assert result["success"] is True
        assert "batch_results" in result
        assert "summary" in result

        # 验证调用次数
        assert mock_process_async.call_count == len(document_ids)

        # 验证统计信息
        summary = result["summary"]
        assert summary["total_documents"] == len(document_ids)
        assert summary["success_count"] == len(document_ids)
        assert summary["error_count"] == 0

    @patch.object(DocumentProcessor, 'process_document_async')
    def test_batch_process_documents_partial_failure(self, mock_process_async, document_processor, mock_db_session):
        """测试批量处理文档 - 部分失败"""
        # 设置模拟
        document_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        mock_process_async.side_effect = [
            {"success": True},
            {"success": False, "error": "Processing failed"},
            {"success": True}
        ]

        # 执行批量处理
        result = document_processor.batch_process_documents(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_ids=document_ids
        )

        # 验证结果
        assert result["success"] is True

        # 验证统计信息
        summary = result["summary"]
        assert summary["total_documents"] == len(document_ids)
        assert summary["success_count"] == 2
        assert summary["error_count"] == 1
        assert summary["success_rate"] == "66.7%"