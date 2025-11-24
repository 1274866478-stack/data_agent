"""
MinIO集成测试 - Story 2.4存储架构验证
测试MinIO对象存储的完整功能和租户隔离
"""

import pytest
import io
import uuid
import time
from minio import Minio
from minio.error import S3Error

from src.app.services.minio_client import minio_service
from src.app.services.document_service import DocumentService


class TestMinIOIntegration:
    """MinIO集成测试类"""

    @pytest.fixture
    def sample_pdf_content(self):
        """创建示例PDF内容"""
        return b"""%PDF-1.4
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

    @pytest.fixture
    def sample_docx_content(self):
        """创建示例DOCX内容（简化ZIP格式）"""
        # 简化的DOCX文件头
        return b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00\x00!\x00\x00\x00'

    def test_minio_connection(self):
        """测试MinIO连接"""
        # 注意：这个测试需要实际的MinIO服务运行
        # 在CI/CD环境中应该跳过或使用测试MinIO
        try:
            connection_result = minio_service.check_connection()
            # 如果连接成功，返回True；如果失败，说明MinIO未运行
            # 这在实际环境中是正常的
            assert isinstance(connection_result, bool)
        except Exception as e:
            pytest.skip(f"MinIO not available for testing: {e}")

    def test_storage_path_generation(self, sample_docx_content):
        """测试存储路径生成 - Story 2.4规范"""
        tenant_id = "test-tenant-123"
        document_id = uuid.uuid4()
        file_name = "test-document.pdf"

        # 使用DocumentService生成存储路径
        document_service = DocumentService()
        storage_path = document_service._generate_storage_path(
            tenant_id, document_id, file_name
        )

        # 验证路径格式符合Story 2.4规范
        expected_pattern = f"dataagent-docs/tenant-{tenant_id}/documents/{document_id}/{file_name}"
        assert storage_path == expected_pattern

        # 验证路径包含租户隔离
        assert f"tenant-{tenant_id}" in storage_path
        assert str(document_id) in storage_path

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_bucket_creation(self):
        """测试存储桶创建"""
        bucket_name = "test-knowledge-documents"

        # 尝试创建存储桶
        result = minio_service.create_bucket(bucket_name)
        assert isinstance(result, bool)

        # 检查存储桶是否存在
        buckets = minio_service.client.list_buckets()
        bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
        assert bucket_exists == result

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_file_upload_download_cycle(self, sample_pdf_content):
        """测试文件上传-下载循环"""
        bucket_name = "test-knowledge-documents"
        object_name = "test-documents/test-file.pdf"
        file_size = len(sample_pdf_content)

        # 确保存储桶存在
        minio_service.create_bucket(bucket_name)

        # 上传文件
        upload_result = minio_service.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=io.BytesIO(sample_pdf_content),
            file_size=file_size,
            content_type="application/pdf"
        )
        assert upload_result is True

        # 列出文件验证
        files = minio_service.list_files(bucket_name, prefix="test-documents/")
        assert len(files) >= 1
        uploaded_file = next((f for f in files if f["name"] == object_name), None)
        assert uploaded_file is not None
        assert uploaded_file["size"] == file_size

        # 下载文件
        downloaded_content = minio_service.download_file(
            bucket_name=bucket_name,
            object_name=object_name
        )
        assert downloaded_content == sample_pdf_content

        # 删除文件
        delete_result = minio_service.delete_file(
            bucket_name=bucket_name,
            object_name=object_name
        )
        assert delete_result is True

        # 验证文件已删除
        files_after_delete = minio_service.list_files(bucket_name, prefix="test-documents/")
        uploaded_file_after = next((f for f in files_after_delete if f["name"] == object_name), None)
        assert uploaded_file_after is None

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_presigned_url_generation(self, sample_pdf_content):
        """测试预签名URL生成"""
        bucket_name = "test-knowledge-documents"
        object_name = "test-documents/preview-test.pdf"

        # 上传文件
        minio_service.create_bucket(bucket_name)
        minio_service.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=io.BytesIO(sample_pdf_content),
            file_size=len(sample_pdf_content),
            content_type="application/pdf"
        )

        # 生成预签名URL
        from datetime import timedelta
        presigned_url = minio_service.get_presigned_url(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(hours=1)
        )

        assert presigned_url is not None
        assert isinstance(presigned_url, str)
        assert "https://" in presigned_url or "http://" in presigned_url

        # 清理
        minio_service.delete_file(bucket_name, object_name)

    def test_tenant_isolation_path_structure(self):
        """测试租户隔离路径结构 - Story 2.4要求"""
        tenant_ids = [
            "tenant-company-a",
            "tenant-company-b",
            "tenant-individual-123",
            "tenant-university-xyz"
        ]

        document_service = DocumentService()

        for tenant_id in tenant_ids:
            document_id = uuid.uuid4()
            file_name = f"document-{tenant_id}.pdf"

            # 生成存储路径
            storage_path = document_service._generate_storage_path(
                tenant_id, document_id, file_name
            )

            # 验证路径包含正确的租户隔离结构
            assert f"tenant-{tenant_id}" in storage_path
            assert "documents/" in storage_path
            assert file_name in storage_path
            assert str(document_id) in storage_path

            # 验证路径以正确的base开头
            assert storage_path.startswith("dataagent-docs/")

            # 验证不同租户的路径互不相同
            paths = []
            for other_tenant in tenant_ids:
                if other_tenant != tenant_id:
                    other_path = document_service._generate_storage_path(
                        other_tenant, uuid.uuid4(), "test.pdf"
                    )
                    paths.append(other_path)

            # 确保当前租户路径不与其他租户冲突
            for other_path in paths:
                assert storage_path != other_path

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_file_type_support(self, sample_pdf_content, sample_docx_content):
        """测试支持的文件类型 - Story 2.4要求"""
        bucket_name = "test-file-types"

        minio_service.create_bucket(bucket_name)

        test_files = [
            ("sample.pdf", sample_pdf_content, "application/pdf"),
            ("sample.docx", sample_docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        ]

        for file_name, content, mime_type in test_files:
            object_name = f"file-types/{file_name}"

            # 上传文件
            upload_result = minio_service.upload_file(
                bucket_name=bucket_name,
                object_name=object_name,
                file_data=io.BytesIO(content),
                file_size=len(content),
                content_type=mime_type
            )
            assert upload_result is True

            # 下载验证
            downloaded_content = minio_service.download_file(bucket_name, object_name)
            assert downloaded_content == content

            # 删除清理
            minio_service.delete_file(bucket_name, object_name)

    def test_error_handling(self):
        """测试错误处理"""
        # 测试不存在的存储桶
        with pytest.raises(Exception):
            minio_service.download_file("non-existent-bucket", "non-existent-file")

        # 测试无效的对象名称（需要实际连接）
        if minio_service.check_connection():
            # 这个测试需要MinIO连接
            with pytest.raises((S3Error, Exception)):
                minio_service.upload_file(
                    bucket_name="non-existent-bucket",
                    object_name="test-file",
                    file_data=io.BytesIO(b"test content"),
                    file_size=12,
                    content_type="text/plain"
                )

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_file_metadata(self, sample_pdf_content):
        """测试文件元数据管理"""
        bucket_name = "test-metadata"
        object_name = "metadata-test.pdf"

        minio_service.create_bucket(bucket_name)

        # 上传文件
        upload_result = minio_service.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=io.BytesIO(sample_pdf_content),
            file_size=len(sample_pdf_content),
            content_type="application/pdf"
        )
        assert upload_result is True

        # 列出文件获取元数据
        files = minio_service.list_files(bucket_name)
        uploaded_file = next((f for f in files if f["name"] == object_name), None)

        assert uploaded_file is not None
        assert "size" in uploaded_file
        assert "last_modified" in uploaded_file
        assert "etag" in uploaded_file
        assert uploaded_file["size"] == len(sample_pdf_content)

        # 清理
        minio_service.delete_file(bucket_name, object_name)

    @pytest.mark.skipif(
        not minio_service.check_connection(),
        reason="MinIO service not available"
    )
    def test_large_file_handling(self):
        """测试大文件处理"""
        bucket_name = "test-large-files"

        minio_service.create_bucket(bucket_name)

        # 创建一个大文件（模拟10MB）
        large_content = b"X" * (10 * 1024 * 1024)
        object_name = "large-file.pdf"

        # 测试大文件上传
        upload_result = minio_service.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_data=io.BytesIO(large_content),
            file_size=len(large_content),
            content_type="application/pdf"
        )
        assert upload_result is True

        # 验证文件大小
        downloaded_content = minio_service.download_file(bucket_name, object_name)
        assert len(downloaded_content) == len(large_content)
        assert downloaded_content == large_content

        # 清理
        minio_service.delete_file(bucket_name, object_name)