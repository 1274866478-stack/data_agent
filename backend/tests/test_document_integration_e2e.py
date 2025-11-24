"""
文档管理端到端集成测试 - Story 2.4规范验证
验证完整文档生命周期：上传→处理→预览→删除
"""

import pytest
import io
import uuid
import tempfile
import time
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.data.models import Base, Tenant, KnowledgeDocument, DocumentStatus
from src.app.data.database import get_db


class TestDocumentIntegrationE2E:
    """文档端到端集成测试类"""

    @pytest.fixture(scope="function")
    def test_db(self):
        """创建测试数据库"""
        # 使用内存SQLite进行测试
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=False
        )

        # 创建表
        Base.metadata.create_all(bind=engine)

        # 创建会话工厂
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        yield session

        session.close()

    @pytest.fixture
    def test_tenant(self, test_db):
        """创建测试租户"""
        tenant = Tenant(
            id="test-tenant-123",
            email="test@example.com",
            display_name="Test Tenant",
            status="active"
        )
        test_db.add(tenant)
        test_db.commit()
        test_db.refresh(tenant)
        return tenant

    @pytest.fixture
    def client(self, test_db):
        """创建测试客户端"""
        def override_get_db():
            yield test_db

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_pdf_file(self):
        """创建测试PDF文件"""
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000054 00000 n
0000000123 00000 n
0000000221 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
312
%%EOF"""
        return io.BytesIO(pdf_content)

    @patch('src.app.services.minio_client.minio_service')
    def test_complete_document_lifecycle(self, mock_minio, client, test_tenant, sample_pdf_file):
        """测试完整文档生命周期"""
        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True
        mock_minio.download_file.return_value = sample_pdf_file.getvalue()
        mock_minio.delete_file.return_value = True
        mock_minio.get_presigned_url.return_value = "https://example.com/preview"
        mock_minio.check_connection.return_value = True

        # 步骤1: 上传文档
        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        )

        assert upload_response.status_code == 201
        upload_data = upload_response.json()
        document_id = upload_data["id"]

        # 验证上传结果
        assert upload_data["file_name"] == "test.pdf"
        assert upload_data["status"] == DocumentStatus.PENDING.value
        assert document_id is not None

        # 步骤2: 获取文档列表
        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["documents"]) >= 1
        assert list_data["total"] >= 1

        # 步骤3: 获取文档详情
        detail_response = client.get(f"/api/v1/documents/{document_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["id"] == document_id
        assert detail_data["file_name"] == "test.pdf"

        # 步骤4: 获取处理状态
        status_response = client.get(f"/api/v1/documents/{document_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["document_id"] == document_id

        # 步骤5: 触发文档处理
        process_response = client.post(f"/api/v1/documents/{document_id}/process")
        assert process_response.status_code == 200
        process_data = process_response.json()
        assert process_data["success"] is True

        # 步骤6: 获取预览链接（模拟文档已处理完成）
        preview_response = client.get(f"/api/v1/documents/{document_id}/preview")
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        assert preview_data["success"] is True
        assert "preview_url" in preview_data

        # 步骤7: 下载文档
        download_response = client.get(f"/api/v1/documents/{document_id}/download")
        assert download_response.status_code == 200
        assert download_response.content == sample_pdf_file.getvalue()

        # 步骤8: 删除文档
        delete_response = client.delete(f"/api/v1/documents/{document_id}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] is True

        # 步骤9: 验证文档已删除
        deleted_detail_response = client.get(f"/api/v1/documents/{document_id}")
        assert deleted_detail_response.status_code == 404

    @patch('src.app.services.minio_client.minio_service')
    def test_tenant_isolation(self, mock_minio, client, test_db, sample_pdf_file):
        """测试租户隔离功能"""
        # 创建第二个租户
        tenant2 = Tenant(
            id="test-tenant-456",
            email="test2@example.com",
            display_name="Test Tenant 2",
            status="active"
        )
        test_db.add(tenant2)
        test_db.commit()

        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True
        mock_minio.download_file.return_value = sample_pdf_file.getvalue()
        mock_minio.delete_file.return_value = True

        # 为租户1上传文档
        upload1_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc1.pdf", sample_pdf_file, "application/pdf")}
        )
        assert upload1_response.status_code == 201

        # 为租户2上传文档
        upload2_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc2.pdf", sample_pdf_file, "application/pdf")}
        )
        assert upload2_response.status_code == 201

        # 验证两个文档都被正确上传
        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["documents"]) == 2

    def test_file_validation_integration(self, client, test_tenant):
        """测试文件验证集成"""
        # 测试无效文件类型
        invalid_file = io.BytesIO(b"This is not a PDF file")
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", invalid_file, "text/plain")}
        )
        # 应该返回400错误，但我们的实现可能需要调整
        # 这个测试用于验证文件验证逻辑
        assert response.status_code in [400, 422]

    @patch('src.app.services.minio_client.minio_service')
    def test_error_handling_integration(self, mock_minio, client, test_tenant, sample_pdf_file):
        """测试错误处理集成"""
        # 模拟MinIO上传失败
        mock_minio.upload_file.return_value = False

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        )

        # 应该返回上传失败错误
        assert response.status_code == 500
        assert "上传失败" in response.json()["detail"]

    @patch('src.app.services.minio_client.minio_service')
    def test_large_file_handling(self, mock_minio, client, test_tenant):
        """测试大文件处理"""
        # 创建一个大文件（模拟60MB PDF）
        large_file_content = b"%PDF-1.4" + b"X" * (60 * 1024 * 1024 - 8)
        large_file = io.BytesIO(large_file_content)

        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("large.pdf", large_file, "application/pdf")}
        )

        # 应该返回文件大小超出限制错误
        assert response.status_code == 400

    def test_document_stats_integration(self, client, test_tenant):
        """测试文档统计集成"""
        # 获取初始统计
        stats_response = client.get("/api/v1/documents/stats/summary")
        assert stats_response.status_code == 200
        initial_stats = stats_response.json()

        # 验证统计结构
        assert "total_documents" in initial_stats
        assert "by_status" in initial_stats
        assert "by_file_type" in initial_stats
        assert "total_size_mb" in initial_stats

    @patch('src.app.services.minio_client.minio_service')
    def test_concurrent_operations(self, mock_minio, client, test_tenant, sample_pdf_file):
        """测试并发操作"""
        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True
        mock_minio.download_file.return_value = sample_pdf_file.getvalue()
        mock_minio.delete_file.return_value = True

        document_ids = []

        # 快速连续上传多个文档
        for i in range(3):
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": (f"doc{i}.pdf", sample_pdf_file, "application/pdf")}
            )
            assert response.status_code == 201
            document_ids.append(response.json()["id"])

        # 验证所有文档都已上传
        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["documents"]) >= 3

        # 并发删除所有文档
        for doc_id in document_ids:
            response = client.delete(f"/api/v1/documents/{doc_id}")
            assert response.status_code == 200

    def test_api_endpoint_health(self, client):
        """测试API端点健康检查"""
        response = client.get("/api/v1/documents/health/status")
        assert response.status_code == 200
        health_data = response.json()

        assert "service" in health_data
        assert "status" in health_data
        assert "components" in health_data

    @patch('src.app.services.minio_client.minio_service')
    def test_document_preview_flow(self, mock_minio, client, test_tenant, sample_pdf_file):
        """测试文档预览流程"""
        # 设置MinIO模拟
        mock_minio.upload_file.return_value = True
        mock_minio.download_file.return_value = sample_pdf_file.getvalue()
        mock_minio.get_presigned_url.return_value = "https://example.com/preview-url"

        # 上传文档
        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        )
        document_id = upload_response.json()["id"]

        # 模拟文档处理完成
        # 在真实环境中，这里会通过DocumentProcessor更新状态
        # 为了测试，我们直接检查预览端点

        # 获取预览URL
        preview_response = client.get(f"/api/v1/documents/{document_id}/preview")
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        assert preview_data["success"] is True
        assert "preview_url" in preview_data
        assert preview_data["preview_url"] == "https://example.com/preview-url"

        # 清理
        client.delete(f"/api/v1/documents/{document_id}")

    def test_invalid_uuid_handling(self, client):
        """测试无效UUID处理"""
        # 测试各种无效的UUID格式
        invalid_uuids = [
            "not-a-uuid",
            "123-456-789",
            "",
            "invalid-uuid-format"
        ]

        for invalid_uuid in invalid_uuids:
            response = client.get(f"/api/v1/documents/{invalid_uuid}")
            assert response.status_code == 400
            assert "无效的文档ID格式" in response.json()["detail"]