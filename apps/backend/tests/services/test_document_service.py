"""
文档服务单元测试 - Story 2.4规范验证
测试文档管理服务的核心功能和边界情况
"""

import pytest
import uuid
import io
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.app.services.document_service import DocumentService
from src.app.data.models import KnowledgeDocument, DocumentStatus, Tenant


class TestDocumentService:
    """文档服务测试类"""

    @pytest.fixture
    def document_service(self):
        """创建文档服务实例"""
        return DocumentService()

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
        session.count = Mock()
        session.order_by = Mock()
        session.offset = Mock()
        session.limit = Mock()
        session.delete = Mock()
        return session

    @pytest.fixture
    def mock_tenant(self):
        """模拟租户对象"""
        tenant = Mock(spec=Tenant)
        tenant.id = "test-tenant-123"
        tenant.email = "test@example.com"
        return tenant

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

        # 添加to_dict方法
        document.to_dict = Mock(return_value={
            "id": str(document.id),
            "tenant_id": document.tenant_id,
            "file_name": document.file_name,
            "storage_path": document.storage_path,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "status": document.status.value,
            "processing_error": document.processing_error,
            "indexed_at": document.indexed_at,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        })

        return document

    @pytest.fixture
    def sample_pdf_file(self):
        """模拟PDF文件数据"""
        return io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")

    def test_file_validation_valid_pdf(self, document_service):
        """测试PDF文件验证 - 有效文件"""
        result = document_service._validate_file(
            file_name="test.pdf",
            file_size=1024 * 1024,  # 1MB
            mime_type="application/pdf"
        )

        assert result["valid"] is True
        assert result["file_type"] == "pdf"
        assert result["max_size_mb"] == 50

    def test_file_validation_valid_docx(self, document_service):
        """测试DOCX文件验证 - 有效文件"""
        result = document_service._validate_file(
            file_name="test.docx",
            file_size=10 * 1024 * 1024,  # 10MB
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        assert result["valid"] is True
        assert result["file_type"] == "docx"
        assert result["max_size_mb"] == 25

    def test_file_validation_unsupported_format(self, document_service):
        """测试文件验证 - 不支持的格式"""
        result = document_service._validate_file(
            file_name="test.txt",
            file_size=1024,
            mime_type="text/plain"
        )

        assert result["valid"] is False
        assert result["error"] == "UPLOAD_001"
        assert "不支持的文件格式" in result["message"]

    def test_file_validation_wrong_mime_type(self, document_service):
        """测试文件验证 - 错误的MIME类型"""
        result = document_service._validate_file(
            file_name="test.pdf",
            file_size=1024,
            mime_type="text/plain"
        )

        assert result["valid"] is False
        assert result["error"] == "UPLOAD_001"
        assert "MIME类型不匹配" in result["message"]

    def test_file_validation_too_large(self, document_service):
        """测试文件验证 - 文件过大"""
        result = document_service._validate_file(
            file_name="test.pdf",
            file_size=100 * 1024 * 1024,  # 100MB
            mime_type="application/pdf"
        )

        assert result["valid"] is False
        assert result["error"] == "UPLOAD_002"
        assert "文件大小超出限制" in result["message"]

    def test_generate_storage_path(self, document_service):
        """测试存储路径生成"""
        tenant_id = "test-tenant-123"
        document_id = uuid.uuid4()
        file_name = "test.pdf"

        path = document_service._generate_storage_path(tenant_id, document_id, file_name)

        expected_pattern = f"dataagent-docs/tenant-{tenant_id}/documents/{document_id}/{file_name}"
        assert path == expected_pattern

    @patch('src.app.services.document_service.minio_service')
    def test_upload_document_success(self, mock_minio, document_service, mock_db_session, mock_tenant, sample_pdf_file):
        """测试文档上传成功"""
        # 设置模拟
        mock_minio.upload_file.return_value = True
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_tenant

        # 执行上传
        result = document_service.upload_document(
            db=mock_db_session,
            tenant_id=mock_tenant.id,
            file_data=sample_pdf_file,
            file_name="test.pdf",
            file_size=len(sample_pdf_file.getvalue()),
            mime_type="application/pdf"
        )

        # 验证结果
        assert result["success"] is True
        assert "document" in result
        assert result["document"]["file_name"] == "test.pdf"
        assert result["document"]["status"] == DocumentStatus.PENDING.value

        # 验证数据库操作
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()

        # 验证MinIO上传
        mock_minio.upload_file.assert_called_once()

    @patch('src.app.services.document_service.minio_service')
    def test_upload_document_minio_failure(self, mock_minio, document_service, mock_db_session, mock_tenant, sample_pdf_file):
        """测试文档上传 - MinIO失败"""
        # 设置模拟
        mock_minio.upload_file.return_value = False
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_tenant

        # 执行上传
        result = document_service.upload_document(
            db=mock_db_session,
            tenant_id=mock_tenant.id,
            file_data=sample_pdf_file,
            file_name="test.pdf",
            file_size=len(sample_pdf_file.getvalue()),
            mime_type="application/pdf"
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "UPLOAD_004"
        assert result["message"] == "文件上传失败，请检查网络连接并重试"

    def test_upload_document_tenant_not_found(self, document_service, mock_db_session, sample_pdf_file):
        """测试文档上传 - 租户不存在"""
        # 设置模拟
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # 执行上传
        result = document_service.upload_document(
            db=mock_db_session,
            tenant_id="nonexistent-tenant",
            file_data=sample_pdf_file,
            file_name="test.pdf",
            file_size=len(sample_pdf_file.getvalue()),
            mime_type="application/pdf"
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "TENANT_NOT_FOUND"
        assert result["message"] == "租户不存在"

    def test_get_documents_success(self, document_service, mock_db_session, mock_document):
        """测试获取文档列表成功"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.all.return_value = [mock_document]

        # 模拟统计信息
        with patch.object(document_service, '_get_document_stats', return_value={"total_documents": 1}):
            # 执行查询
            result = document_service.get_documents(
                db=mock_db_session,
                tenant_id="test-tenant-123"
            )

        # 验证结果
        assert result["success"] is True
        assert "documents" in result
        assert "total" in result
        assert "stats" in result
        assert len(result["documents"]) == 1
        assert result["total"] == 1

    def test_get_document_by_id_success(self, document_service, mock_db_session, mock_document):
        """测试根据ID获取文档成功"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行查询
        result = document_service.get_document_by_id(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is True
        assert "document" in result
        assert result["document"]["id"] == str(mock_document.id)

    def test_get_document_by_id_not_found(self, document_service, mock_db_session):
        """测试根据ID获取文档 - 未找到"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # 执行查询
        result = document_service.get_document_by_id(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=uuid.uuid4()
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "DOCUMENT_NOT_FOUND"

    def test_update_document_status_success(self, document_service, mock_db_session, mock_document):
        """测试更新文档状态成功"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行更新
        result = document_service.update_document_status(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=mock_document.id,
            status=DocumentStatus.READY
        )

        # 验证结果
        assert result["success"] is True
        assert "document" in result
        assert result["document"]["status"] == DocumentStatus.READY.value
        assert mock_document.indexed_at is not None  # 应该设置indexed_at

    @patch('src.app.services.document_service.minio_service')
    def test_delete_document_success(self, mock_minio, document_service, mock_db_session, mock_document):
        """测试删除文档成功"""
        # 设置模拟
        mock_minio.delete_file.return_value = True
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行删除
        result = document_service.delete_document(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is True
        assert "deleted_document" in result
        assert result["deleted_document"]["id"] == str(mock_document.id)

        # 验证MinIO删除
        mock_minio.delete_file.assert_called_once()

    @patch('src.app.services.document_service.minio_service')
    def test_get_document_preview_url_success(self, mock_minio, document_service, mock_db_session, mock_document):
        """测试获取文档预览URL成功"""
        # 设置模拟
        mock_minio.get_presigned_url.return_value = "https://example.com/preview-url"
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行获取预览URL
        result = document_service.get_document_preview_url(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is True
        assert "preview_url" in result
        assert result["preview_url"] == "https://example.com/preview-url"

    def test_get_document_preview_url_not_ready(self, document_service, mock_db_session, mock_document):
        """测试获取文档预览URL - 文档未准备就绪"""
        # 设置文档状态为PENDING
        mock_document.status = DocumentStatus.PENDING

        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_document

        # 执行获取预览URL
        result = document_service.get_document_preview_url(
            db=mock_db_session,
            tenant_id="test-tenant-123",
            document_id=mock_document.id
        )

        # 验证结果
        assert result["success"] is False
        assert result["error"] == "DOCUMENT_NOT_READY"

    def test_get_document_stats_success(self, document_service, mock_db_session, mock_document):
        """测试获取文档统计信息成功"""
        # 设置模拟
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [
            (DocumentStatus.READY, 5),
            (DocumentStatus.PENDING, 2)
        ]

        # 执行统计查询
        stats = document_service._get_document_stats(mock_db_session, "test-tenant-123")

        # 验证结果
        assert stats is not None
        assert "by_status" in stats
        assert "total_documents" in stats
        assert stats["by_status"]["READY"] == 5
        assert stats["by_status"]["PENDING"] == 2