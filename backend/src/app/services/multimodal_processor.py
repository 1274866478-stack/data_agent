"""
# [MULTIMODAL_PROCESSOR] 多模态内容处理器

## [HEADER]
**文件名**: multimodal_processor.py
**职责**: 处理图片、音频、视频等多媒体内容，集成MinIO存储和外部URL下载
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 多模态内容处理器

## [INPUT]
- **file_data: bytes** - 文件二进制数据
- **original_filename: str** - 原始文件名
- **tenant_id: str** - 租户ID
- **media_type: Optional[str]** - 媒体类型（image/audio/video），如果不指定则自动检测
- **content_list: List[Dict[str, Any]]** - 内容列表（包含image_url, input_audio, video_url等）
- **object_name: str** - MinIO对象名称
- **expires_hours: int** - 预签名URL有效期（小时）
- **url: str** - 外部URL
- **content_type: str** - 内容类型

## [OUTPUT]
- **Optional[Dict[str, Any]]**: 上传结果信息
  - object_name: MinIO对象名称
  - original_filename: 原始文件名
  - media_type: 媒体类型
  - size: 文件大小
  - mime_type: MIME类型
  - presigned_url: 预签名URL（24小时有效）
  - tenant_id: 租户ID
  - uploaded_at: 上传时间
- **List[Dict[str, Any]]**: 处理后的内容列表
- **Optional[Dict[str, Any]]**: 文件信息
- **bool**: 操作成功标识
- **Optional[str]**: 预签名URL
- **int**: 清理数量

**上游依赖** (已读取源码):
- 项目配置: src.app.core.config.settings

**下游依赖** (需要反向索引分析):
- [llm_service.py](./llm_service.py) - LLM服务处理多模态内容
- [document_service.py](./document_service.py) - 文档服务处理多媒体附件

**调用方**:
- LLM服务处理多模态输入
- 文档上传服务处理图片/视频附件
- Agent服务处理多媒体内容

## [STATE]
- **MinIO客户端**: minio_client（Minio实例）
- **存储桶名称**: bucket_name（默认multimodal-content）
- **最大文件大小**: max_file_size（默认50MB）
- **允许的扩展名**: allowed_extensions字典
  - image: .jpg, .jpeg, .png, .gif, .webp, .bmp
  - audio: .wav, .mp3, .ogg, .flac, .aac, .m4a
  - video: .mp4, .avi, .mov, .mkv, .webm, .flv
- **MIME类型检测**: mimetypes.guess_type
- **媒体类型判断**: get_media_type（根据扩展名）
- **文件命名**: {tenant_id}/{media_type}/{uuid}.{ext}
- **预签名URL有效期**: 24小时
- **外部URL下载**: _download_and_upload（aiohttp.ClientSession）
- **内容列表处理**: process_content_list（自动转换image_url, input_audio, video_url）
- **文件信息获取**: get_file_info（MinIO stat_object）
- **文件删除**: delete_file（MinIO remove_object）
- **过期清理**: cleanup_expired_urls（待实现）

## [SIDE-EFFECTS]
- **MinIO操作**: minio_client.bucket_exists检查桶，minio_client.make_bucket创建桶
- **MinIO上传**: minio_client.put_object上传文件到multimodal-content桶
- **预签名URL**: minio_client.presigned_get_object生成24小时有效URL
- **MinIO下载**: minio_client.stat_object获取文件信息
- **MinIO删除**: minio_client.remove_object删除文件
- **文件大小检查**: len(file_data) > self.max_file_size验证
- **路径分割**: os.path.splitext提取文件扩展名
- **MIME检测**: mimetypes.guess_type猜测文件类型
- **UUID生成**: uuid.uuid4()生成唯一文件名
- **字节流**: io.BytesIO(file_data)包装文件数据
- **HTTP下载**: aiohttp.ClientSession().get()下载外部URL
- **异步读取**: await response.read()读取文件数据
- **URL解析**: os.path.basename提取文件名
- **字典操作**: url_info.get("url")获取URL
- **条件判断**: original_url.startswith(("http://", "https://"))判断外部URL
- **列表追加**: processed_content.append添加处理后的内容
- **异常处理**: try-except捕获所有异常，返回None或保留原始内容
- **日志记录**: logger.info/error/warning记录操作
- **全局单例**: multimodal_processor全局实例

## [POS]
**路径**: backend/src/app/services/multimodal_processor.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 依赖项目配置settings
"""

import os
import uuid
import mimetypes
import asyncio
import io
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp

from minio import Minio
from minio.error import S3Error
import logging

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class MultimodalProcessor:
    """多模态内容处理器"""

    def __init__(self):
        """初始化多模态处理器"""
        self.minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=getattr(settings, 'minio_secure', False)
        )
        self.bucket_name = getattr(settings, 'minio_multimodal_bucket', 'multimodal-content')
        self.max_file_size = getattr(settings, 'multimodal_max_file_size', 50 * 1024 * 1024)  # 50MB
        self.allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
            'audio': ['.wav', '.mp3', '.ogg', '.flac', '.aac', '.m4a'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
        }

    async def ensure_bucket_exists(self) -> bool:
        """确保存储桶存在"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"创建多模态存储桶: {self.bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"创建存储桶失败: {e}")
            return False

    def get_content_type(self, file_path: str) -> str:
        """获取文件MIME类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def get_media_type(self, file_path: str) -> Optional[str]:
        """根据文件扩展名判断媒体类型"""
        _, ext = os.path.splitext(file_path.lower())

        for media_type, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return media_type
        return None

    async def upload_file(
        self,
        file_data: bytes,
        original_filename: str,
        tenant_id: str,
        media_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        上传文件到MinIO

        Args:
            file_data: 文件二进制数据
            original_filename: 原始文件名
            tenant_id: 租户ID
            media_type: 媒体类型，如果不指定则自动检测

        Returns:
            Dict: 上传结果信息
        """
        try:
            # 检查文件大小
            if len(file_data) > self.max_file_size:
                logger.error(f"文件过大: {len(file_data)} > {self.max_file_size}")
                return None

            # 检测媒体类型
            if media_type is None:
                media_type = self.get_media_type(original_filename)
                if not media_type:
                    logger.error(f"不支持的文件类型: {original_filename}")
                    return None

            # 确保存储桶存在
            if not await self.ensure_bucket_exists():
                return None

            # 生成唯一文件名
            file_ext = os.path.splitext(original_filename)[1]
            unique_filename = f"{tenant_id}/{media_type}/{uuid.uuid4()}{file_ext}"

            # 上传到MinIO
            mime_type = self.get_content_type(original_filename)
            result = self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=unique_filename,
                data=io.BytesIO(file_data),
                length=len(file_data),
                content_type=mime_type
            )

            # 生成预签名URL（有效期24小时）
            presigned_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=unique_filename,
                expires=timedelta(hours=24)
            )

            logger.info(f"文件上传成功: {unique_filename}")

            return {
                "object_name": unique_filename,
                "original_filename": original_filename,
                "media_type": media_type,
                "size": len(file_data),
                "mime_type": mime_type,
                "presigned_url": presigned_url,
                "tenant_id": tenant_id,
                "uploaded_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return None

    async def process_content_list(
        self,
        content_list: List[Dict[str, Any]],
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        处理内容列表，自动上传文件并转换格式

        Args:
            content_list: 内容列表
            tenant_id: 租户ID

        Returns:
            List: 处理后的内容列表
        """
        processed_content = []

        for item in content_list:
            try:
                content_type = item.get("type")

                if content_type in ["image_url", "input_audio", "video_url"]:
                    # 处理多媒体内容
                    url_info = item.get(f"{content_type}", {})
                    original_url = url_info.get("url", "")

                    if original_url:
                        # 如果是外部URL，下载并上传到MinIO
                        if original_url.startswith(("http://", "https://")):
                            upload_result = await self._download_and_upload(
                                original_url, tenant_id, content_type
                            )
                            if upload_result:
                                processed_content.append({
                                    "type": content_type,
                                    content_type.replace("_url", ""): {
                                        "url": upload_result["presigned_url"],
                                        "original_url": original_url,
                                        "object_name": upload_result["object_name"],
                                        "size": upload_result["size"]
                                    }
                                })
                            else:
                                # 如果上传失败，保留原始URL
                                processed_content.append(item)
                        else:
                            # 本地文件或已有URL，直接使用
                            processed_content.append(item)
                    else:
                        # 没有URL，跳过
                        continue

                elif content_type == "text":
                    # 文本内容直接保留
                    processed_content.append(item)

                else:
                    # 其他类型暂时保留
                    processed_content.append(item)

            except Exception as e:
                logger.warning(f"处理内容项失败: {e}, 内容: {item}")
                # 处理失败时保留原始内容
                processed_content.append(item)

        return processed_content

    async def _download_and_upload(
        self,
        url: str,
        tenant_id: str,
        content_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        下载外部URL并上传到MinIO

        Args:
            url: 外部URL
            tenant_id: 租户ID
            content_type: 内容类型

        Returns:
            Dict: 上传结果
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        file_data = await response.read()

                        # 从URL提取文件名
                        filename = os.path.basename(url.split('?')[0])
                        if not filename:
                            # 根据内容类型生成文件名
                            extension_map = {
                                "image_url": "image.jpg",
                                "input_audio": "audio.wav",
                                "video_url": "video.mp4"
                            }
                            filename = extension_map.get(content_type, "file")

                        return await self.upload_file(
                            file_data=file_data,
                            original_filename=filename,
                            tenant_id=tenant_id,
                            media_type=content_type.replace("_url", "")
                        )
                    else:
                        logger.error(f"下载文件失败: HTTP {response.status}")
                        return None

        except Exception as e:
            logger.error(f"下载上传文件失败: {e}")
            return None

    async def get_file_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            stat = self.minio_client.stat_object(self.bucket_name, object_name)
            return {
                "object_name": object_name,
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat(),
                "content_type": stat.content_type,
                "etag": stat.etag
            }
        except S3Error as e:
            logger.error(f"获取文件信息失败: {e}")
            return None

    async def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        try:
            self.minio_client.remove_object(self.bucket_name, object_name)
            logger.info(f"文件删除成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件删除失败: {e}")
            return False

    async def get_presigned_url(
        self,
        object_name: str,
        expires_hours: int = 24
    ) -> Optional[str]:
        """获取预签名URL"""
        try:
            return self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_hours)
            )
        except S3Error as e:
            logger.error(f"获取预签名URL失败: {e}")
            return None

    async def cleanup_expired_urls(self, tenant_id: str = None) -> int:
        """
        清理过期的文件（可选功能）

        Args:
            tenant_id: 如果指定，只清理该租户的文件

        Returns:
            int: 清理的文件数量
        """
        # 这是一个高级功能，可以根据需要实现
        # 通常使用MinIO的生命周期策略更高效
        logger.info("清理过期文件功能待实现")
        return 0


# 全局多模态处理器实例
multimodal_processor = MultimodalProcessor()