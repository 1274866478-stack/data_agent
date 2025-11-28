"""
MinIO 客户端配置和操作
MinIO 连接、桶操作、文件上传下载
"""

from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import io
import logging
from datetime import datetime, timedelta

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOService:
    """
    MinIO 对象存储服务类
    """

    def __init__(self):
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.default_bucket = "knowledge-documents"

    def check_connection(self) -> bool:
        """
        检查MinIO连接状态
        """
        try:
            # 尝试列出存储桶来验证连接
            self.client.list_buckets()
            logger.info("MinIO connection: OK")
            return True
        except Exception as e:
            logger.error(f"MinIO connection failed: {e}")
            return False

    def create_bucket(self, bucket_name: str) -> bool:
        """
        创建存储桶
        """
        try:
            if not self.client.bucket_exists(bucket_name=bucket_name):
                self.client.make_bucket(bucket_name=bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully")
            return True
        except S3Error as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            return False

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: Optional[str] = None
    ) -> bool:
        """
        上传文件到MinIO
        """
        try:
            # 确保存储桶存在
            self.create_bucket(bucket_name)

            # 上传文件
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )

            logger.info(f"File uploaded successfully: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload file '{object_name}': {e}")
            return False

    def download_file(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        从MinIO下载文件
        """
        try:
            response = self.client.get_object(bucket_name=bucket_name, object_name=object_name)
            file_data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"File downloaded successfully: {object_name}")
            return file_data
        except S3Error as e:
            logger.error(f"Failed to download file '{object_name}': {e}")
            return None

    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        """
        从MinIO删除文件
        """
        try:
            self.client.remove_object(bucket_name=bucket_name, object_name=object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete file '{object_name}': {e}")
            return False

    def list_files(self, bucket_name: str, prefix: Optional[str] = None) -> list:
        """
        列出存储桶中的文件
        """
        try:
            objects = self.client.list_objects(bucket_name=bucket_name, prefix=prefix)
            files = []
            for obj in objects:
                files.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })
            return files
        except S3Error as e:
            logger.error(f"Failed to list files in bucket '{bucket_name}': {e}")
            return []

    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """
        生成预签名URL用于文件访问
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for '{object_name}': {e}")
            return None


# 全局MinIO服务实例
minio_service = MinIOService()