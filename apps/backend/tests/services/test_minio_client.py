"""
MinIO 服务测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import io

from src.app.services.minio_client import MinIOService


class TestMinIOService:
    """MinIO 服务测试类"""

    @pytest.fixture
    def minio_service(self):
        """创建MinIO服务实例"""
        return MinIOService()

    def test_init(self):
        """测试MinIO服务初始化"""
        with patch('src.app.services.minio_client.Minio') as mock_minio:
            minio_service = MinIOService()
            mock_minio.assert_called_once()
            assert minio_service.default_bucket == "knowledge-documents"

    @patch('src.app.services.minio_client.Minio')
    def test_check_connection_success(self, mock_minio_class):
        """测试成功检查MinIO连接"""
        mock_client = Mock()
        mock_client.list_buckets.return_value = []
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.check_connection()

        assert result is True
        mock_client.list_buckets.assert_called_once()

    @patch('src.app.services.minio_client.Minio')
    def test_check_connection_failure(self, mock_minio_class):
        """测试MinIO连接检查失败"""
        mock_client = Mock()
        mock_client.list_buckets.side_effect = Exception("Connection failed")
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.check_connection()

        assert result is False

    @patch('src.app.services.minio_client.Minio')
    def test_create_bucket_new(self, mock_minio_class):
        """测试创建新存储桶"""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = False
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.create_bucket("test-bucket")

        assert result is True
        mock_client.bucket_exists.assert_called_with("test-bucket")
        mock_client.make_bucket.assert_called_with("test-bucket")

    @patch('src.app.services.minio_client.Minio')
    def test_create_bucket_existing(self, mock_minio_class):
        """测试创建已存在的存储桶"""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.create_bucket("test-bucket")

        assert result is True
        mock_client.bucket_exists.assert_called_with("test-bucket")
        mock_client.make_bucket.assert_not_called()

    @patch('src.app.services.minio_client.Minio')
    def test_upload_file_success(self, mock_minio_class):
        """测试成功上传文件"""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = Mock()
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        file_data = io.BytesIO(b"test file content")
        result = minio_service.upload_file(
            bucket_name="test-bucket",
            object_name="test-file.txt",
            file_data=file_data,
            file_size=17,
            content_type="text/plain"
        )

        assert result is True
        mock_client.put_object.assert_called_once()

    @patch('src.app.services.minio_client.Minio')
    def test_download_file_success(self, mock_minio_class):
        """测试成功下载文件"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.read.return_value = b"test file content"
        mock_client.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.download_file("test-bucket", "test-file.txt")

        assert result == b"test file content"
        mock_client.get_object.assert_called_with("test-bucket", "test-file.txt")
        mock_response.read.assert_called_once()
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    @patch('src.app.services.minio_client.Minio')
    def test_delete_file_success(self, mock_minio_class):
        """测试成功删除文件"""
        mock_client = Mock()
        mock_client.remove_object.return_value = None
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.delete_file("test-bucket", "test-file.txt")

        assert result is True
        mock_client.remove_object.assert_called_with("test-bucket", "test-file.txt")

    @patch('src.app.services.minio_client.Minio')
    def test_list_files_success(self, mock_minio_class):
        """测试成功列出文件"""
        mock_client = Mock()
        mock_obj1 = Mock()
        mock_obj1.object_name = "file1.txt"
        mock_obj1.size = 100
        mock_obj1.last_modified = "2023-01-01T00:00:00Z"
        mock_obj1.etag = "etag1"

        mock_obj2 = Mock()
        mock_obj2.object_name = "file2.txt"
        mock_obj2.size = 200
        mock_obj2.last_modified = "2023-01-02T00:00:00Z"
        mock_obj2.etag = "etag2"

        mock_client.list_objects.return_value = [mock_obj1, mock_obj2]
        mock_minio_class.return_value = mock_client

        minio_service = MinIOService()
        result = minio_service.list_files("test-bucket")

        assert len(result) == 2
        assert result[0]["name"] == "file1.txt"
        assert result[0]["size"] == 100
        assert result[1]["name"] == "file2.txt"
        assert result[1]["size"] == 200

    @patch('src.app.services.minio_client.Minio')
    def test_get_presigned_url_success(self, mock_minio_class):
        """测试成功生成预签名URL"""
        mock_client = Mock()
        mock_client.presigned_get_object.return_value = "http://localhost:9000/test-bucket/test-file.txt?expires=123456789"
        mock_minio_class.return_value = mock_client

        from datetime import timedelta
        minio_service = MinIOService()
        result = minio_service.get_presigned_url("test-bucket", "test-file.txt", timedelta(hours=1))

        assert result == "http://localhost:9000/test-bucket/test-file.txt?expires=123456789"
        mock_client.presigned_get_object.assert_called_once()