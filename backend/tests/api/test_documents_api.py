"""
文档API集成测试 - Story 2.4规范验证
测试文档管理API端点的完整功能和响应
"""

import pytest
import io
import json
import uuid
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.main import app
from src.app.data.models import KnowledgeDocument, DocumentStatus, Tenant


class TestDocumentsAPI:
    """文档API测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = Mock(spec=Session)
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
        document.file_size = 1024 * 1024
        document.mime_type = "application/pdf"
        document.status = DocumentStatus.READY
        document.processing_error = None
        document.indexed_at = "2025-11-17T12:00:00Z"
        document.created_at = "2025-11-17T10:00:00Z"
        document.updated_at = "2025-11-17T12:00:00Z"

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
            "created_at": document.created_at,
            "updated_at": document.updated_at
        })

        return document

    @pytest.fixture
    def sample_pdf_file(self):
        """模拟PDF文件"""
        return io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_documents_success(self, mock_service, mock_get_db, client, mock_document):
        """测试获取文档列表成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_documents.return_value = {
            "success": True,
            "documents": [mock_document.to_dict()],
            "total": 1,
            "skip": 0,
            "limit": 100,
            "stats": {"total_documents": 1}
        }

        # 执行请求
        response = client.get("/api/v1/documents")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "documents" in data
        assert "total" in data
        assert len(data["documents"]) == 1

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_documents_with_filters(self, mock_service, mock_get_db, client):
        """测试获取文档列表 - 带过滤条件"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_documents.return_value = {
            "success": True,
            "documents": [],
            "total": 0,
            "skip": 0,
            "limit": 100,
            "stats": {"total_documents": 0}
        }

        # 执行带过滤的请求
        response = client.get("/api/v1/documents?status=READY&file_type=pdf&skip=0&limit=50")

        # 验证响应
        assert response.status_code == 200

        # 验证服务调用参数
        mock_service.get_documents.assert_called_once()
        call_args = mock_service.get_documents.call_args[1]
        assert call_args["status"] == DocumentStatus.READY
        assert call_args["file_type"] == "pdf"
        assert call_args["skip"] == 0
        assert call_args["limit"] == 50

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_documents_invalid_status(self, mock_service, mock_get_db, client):
        """测试获取文档列表 - 无效状态"""
        # 设置模拟
        mock_get_db.return_value = Mock()

        # 执行带无效状态的请求
        response = client.get("/api/v1/documents?status=INVALID_STATUS")

        # 验证响应
        assert response.status_code == 400
        assert "无效的状态值" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_document_by_id_success(self, mock_service, mock_get_db, client, mock_document):
        """测试根据ID获取文档成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_document_by_id.return_value = {
            "success": True,
            "document": mock_document.to_dict()
        }

        # 执行请求
        response = client.get(f"/api/v1/documents/{mock_document.id}")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_document.id)
        assert data["file_name"] == mock_document.file_name

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_document_by_id_not_found(self, mock_service, mock_get_db, client):
        """测试根据ID获取文档 - 未找到"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_document_by_id.return_value = {
            "success": False,
            "error": "DOCUMENT_NOT_FOUND",
            "message": "文档不存在或无权访问"
        }

        doc_id = uuid.uuid4()
        # 执行请求
        response = client.get(f"/api/v1/documents/{doc_id}")

        # 验证响应
        assert response.status_code == 404
        assert "文档不存在或无权访问" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_upload_document_success(self, mock_service, mock_get_db, client, sample_pdf_file):
        """测试文档上传成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.upload_document.return_value = {
            "success": True,
            "document": {
                "id": str(uuid.uuid4()),
                "file_name": "test.pdf",
                "status": DocumentStatus.PENDING.value
            }
        }

        # 执行上传请求
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        )

        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["status"] == DocumentStatus.PENDING.value

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_upload_document_invalid_file_type(self, mock_service, mock_get_db, client):
        """测试文档上传 - 无效文件类型"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.upload_document.return_value = {
            "success": False,
            "error": "UPLOAD_001",
            "message": "不支持的文件格式"
        }

        # 执行上传请求
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
        )

        # 验证响应
        assert response.status_code == 400
        assert "不支持的文件格式" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_upload_document_no_file(self, mock_service, mock_get_db, client):
        """测试文档上传 - 无文件"""
        # 设置模拟
        mock_get_db.return_value = Mock()

        # 执行上传请求
        response = client.post("/api/v1/documents/upload")

        # 验证响应
        assert response.status_code == 422  # Validation error

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_delete_document_success(self, mock_service, mock_get_db, client, mock_document):
        """测试删除文档成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.delete_document.return_value = {
            "success": True,
            "message": "文档删除成功"
        }

        # 执行删除请求
        response = client.delete(f"/api/v1/documents/{mock_document.id}")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "文档删除成功" in data["message"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_delete_document_not_found(self, mock_service, mock_get_db, client):
        """测试删除文档 - 未找到"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.delete_document.return_value = {
            "success": False,
            "error": "DOCUMENT_NOT_FOUND",
            "message": "文档不存在或无权访问"
        }

        doc_id = uuid.uuid4()
        # 执行删除请求
        response = client.delete(f"/api/v1/documents/{doc_id}")

        # 验证响应
        assert response.status_code == 404
        assert "文档不存在或无权访问" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    @patch('src.app.api.v1.endpoints.documents.minio_service')
    def test_download_document_success(self, mock_minio, mock_service, mock_get_db, client, mock_document):
        """测试文档下载成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_document_by_id.return_value = {
            "success": True,
            "document": mock_document.to_dict()
        }
        mock_minio.download_file.return_value = b"file content"

        # 执行下载请求
        response = client.get(f"/api/v1/documents/{mock_document.id}/download")

        # 验证响应
        assert response.status_code == 200
        assert response.content == b"file content"
        assert "attachment" in response.headers["content-disposition"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_document_preview_success(self, mock_service, mock_get_db, client, mock_document):
        """测试获取文档预览链接成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_document_preview_url.return_value = {
            "success": True,
            "preview_url": "https://example.com/preview-url",
            "document": mock_document.to_dict()
        }

        # 执行预览请求
        response = client.get(f"/api/v1/documents/{mock_document.id}/preview")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["preview_url"] == "https://example.com/preview-url"

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_document_preview_not_ready(self, mock_service, mock_get_db, client, mock_document):
        """测试获取文档预览链接 - 文档未准备就绪"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_document_preview_url.return_value = {
            "success": False,
            "error": "DOCUMENT_NOT_READY",
            "message": "文档尚未处理完成，无法预览"
        }

        # 执行预览请求
        response = client.get(f"/api/v1/documents/{mock_document.id}/preview")

        # 验证响应
        assert response.status_code == 400
        assert "文档尚未处理完成，无法预览" in response.json()["detail"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_processor')
    def test_get_document_processing_status(self, mock_processor, mock_get_db, client, mock_document):
        """测试获取文档处理状态"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_processor.get_processing_status.return_value = {
            "success": True,
            "document_id": str(mock_document.id),
            "status": DocumentStatus.READY.value,
            "indexed_at": "2025-11-17T12:00:00Z"
        }

        # 执行状态请求
        response = client.get(f"/api/v1/documents/{mock_document.id}/status")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == DocumentStatus.READY.value

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_processor')
    def test_process_document_success(self, mock_processor, mock_get_db, client, mock_document):
        """测试触发文档处理成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_processor.process_document_async.return_value = {
            "success": True,
            "document_id": str(mock_document.id),
            "message": "文档处理完成"
        }

        # 执行处理请求
        response = client.post(f"/api/v1/documents/{mock_document.id}/process")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "文档处理完成" in data["message"]

    @patch('src.app.api.v1.endpoints.documents.get_db')
    @patch('src.app.api.v1.endpoints.documents.document_service')
    def test_get_document_stats_success(self, mock_service, mock_get_db, client):
        """测试获取文档统计信息成功"""
        # 设置模拟
        mock_get_db.return_value = Mock()
        mock_service.get_documents.return_value = {
            "success": True,
            "documents": [],
            "stats": {
                "by_status": {DocumentStatus.READY.value: 5, DocumentStatus.PENDING.value: 2},
                "by_file_type": {"pdf": 7},
                "total_documents": 7,
                "total_size_bytes": 1024 * 1024 * 10,
                "total_size_mb": 10.0
            }
        }

        # 执行统计请求
        response = client.get("/api/v1/documents/stats/summary")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 7
        assert data["by_file_type"]["pdf"] == 7
        assert data["total_size_mb"] == 10.0

    @patch('src.app.api.v1.endpoints.documents.minio_service')
    def test_documents_health_check(self, mock_minio, client):
        """测试文档服务健康检查"""
        # 设置模拟
        mock_minio.check_connection.return_value = True

        # 执行健康检查请求
        response = client.get("/api/v1/documents/health/status")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "documents"
        assert data["status"] == "healthy"
        assert "components" in data

    def test_invalid_document_id_format(self, client):
        """测试无效的文档ID格式"""
        # 执行请求
        response = client.get("/api/v1/documents/invalid-uuid")

        # 验证响应
        assert response.status_code == 400
        assert "无效的文档ID格式" in response.json()["detail"]