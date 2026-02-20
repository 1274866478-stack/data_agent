"""
# [MINIO_CLIENT] MinIO对象存储客户端

## [HEADER]
**文件名**: minio_client.py
**职责**: 提供MinIO对象存储连接、存储桶管理、文件上传下载、预签名URL生成和文件列表功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - MinIO对象存储服务

## [INPUT]
- **bucket_name: str** - 存储桶名称
- **object_name: str** - 对象名称（文件路径）
- **file_data: BinaryIO** - 文件数据二进制流
- **file_size: int** - 文件大小（字节）
- **content_type: Optional[str]** - 文件MIME类型（如'application/pdf'）
- **prefix: Optional[str]** - 文件路径前缀（用于列表过滤）
- **expires: timedelta** - 预签名URL过期时间（默认1小时）

## [OUTPUT]
- **bool**: 操作成功/失败（create_bucket, upload_file, delete_file）
- **bool**: 连接状态（check_connection）
- **Optional[bytes]**: 文件二进制数据（download_file）
- **list**: 文件元数据列表（list_files）
  - name: str - 文件名
  - size: int - 文件大小
  - last_modified: datetime - 最后修改时间
  - etag: str - 文件ETag
- **Optional[str]**: 预签名URL（get_presigned_url）

**上游依赖** (已读取源码):
- [./core/config.py](./core/config.py) - 配置管理（MinIO endpoint, access_key, secret_key, secure）

**下游依赖** (需要反向索引分析):
- [document_service.py](./document_service.py) - 文档上传下载
- [../api/v1/endpoints/documents.py](../api/v1/endpoints/documents.py) - 文档API端点

**调用方**:
- 文档上传流程（KnowledgeDocument创建后）
- 文档下载API
- MinIO健康检查端点

## [STATE]
- **客户端初始化**: 构造函数中创建Minio客户端实例
- **默认存储桶**: default_bucket = "knowledge-documents"
- **连接配置**: 从settings读取endpoint, access_key, secret_key, secure
- **全局实例**: minio_service单例供全局使用

## [SIDE-EFFECTS]
- **HTTP连接**: 连接MinIO服务（settings.minio_endpoint）
- **存储桶操作**: 自动创建不存在的存储桶（upload_file中）
- **文件I/O**: 读写文件二进制流
- **网络传输**: 上传/下载大文件时的网络流量
- **异常处理**: S3Error捕获和日志记录
- **资源管理**: download_file后关闭response和释放连接

## [POS]
**路径**: backend/src/app/services/minio_client.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 core.config
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