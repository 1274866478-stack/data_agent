#!/usr/bin/env python3
"""
MinIO资源上传脚本
用于上传logo、图标等静态资源到MinIO存储桶
"""

import os
import sys
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from src.services.minio_client import minio_client
from src.core.config import settings
from src.core.logging import logger


class AssetUploader:
    """资源上传管理器"""

    def __init__(self):
        self.client = minio_client
        self.bucket_name = settings.MINIO_BUCKET_NAME

    async def ensure_bucket_exists(self) -> bool:
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"✅ 创建存储桶: {self.bucket_name}")
            else:
                logger.info(f"✅ 存储桶已存在: {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 存储桶操作失败: {e}")
            return False

    def get_content_type(self, file_path: Path) -> str:
        """获取文件MIME类型"""
        content_type, _ = mimetypes.guess_type(str(file_path))
        return content_type or "application/octet-stream"

    async def upload_file(
        self,
        file_path: Path,
        object_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        上传单个文件到MinIO

        Args:
            file_path: 本地文件路径
            object_name: MinIO对象名称，默认使用文件名
            metadata: 文件元数据

        Returns:
            bool: 上传是否成功
        """
        if not file_path.exists():
            logger.error(f"❌ 文件不存在: {file_path}")
            return False

        # 使用文件名作为对象名（如果未指定）
        if object_name is None:
            object_name = file_path.name

        # 构建完整的对象路径
        full_object_name = f"assets/{object_name}"

        try:
            # 准备元数据
            file_metadata = {
                "Content-Type": self.get_content_type(file_path),
                "X-Upload-Time": str(int(Path().resolve().stat().st_mtime)),
                "X-Original-Name": file_path.name,
                "X-Project": "data-agent-v4",
                "X-Version": "4.1"
            }

            # 添加自定义元数据
            if metadata:
                file_metadata.update(metadata)

            # 上传文件
            result = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=full_object_name,
                file_path=str(file_path),
                metadata=file_metadata
            )

            logger.info(f"✅ 文件上传成功:")
            logger.info(f"   本地路径: {file_path}")
            logger.info(f"   对象名称: {full_object_name}")
            logger.info(f"   文件大小: {result.size} bytes")
            logger.info(f"   ETag: {result.etag}")

            return True

        except Exception as e:
            logger.error(f"❌ 文件上传失败 {file_path}: {e}")
            return False

    async def upload_directory(
        self,
        directory: Path,
        prefix: str = "",
        recursive: bool = True
    ) -> List[str]:
        """
        上传目录中的所有文件

        Args:
            directory: 目录路径
            prefix: MinIO对象前缀
            recursive: 是否递归上传子目录

        Returns:
            List[str]: 成功上传的文件列表
        """
        if not directory.exists() or not directory.is_dir():
            logger.error(f"❌ 目录不存在或不是有效目录: {directory}")
            return []

        # 获取文件列表
        if recursive:
            file_pattern = "**/*"
        else:
            file_pattern = "*"

        files = [f for f in directory.glob(file_pattern) if f.is_file()]

        if not files:
            logger.warning(f"⚠️ 目录中没有找到文件: {directory}")
            return []

        logger.info(f"📁 开始上传目录: {directory} (共{len(files)}个文件)")

        successful_uploads = []

        for file_path in files:
            # 构建对象名称
            relative_path = file_path.relative_to(directory)
            object_name = f"{prefix}{relative_path}".replace("\\", "/")

            success = await self.upload_file(file_path, object_name)
            if success:
                successful_uploads.append(str(file_path))

        logger.info(f"✅ 目录上传完成: {len(successful_uploads)}/{len(files)} 个文件上传成功")
        return successful_uploads

    async def get_file_url(self, object_name: str, expires_in_hours: int = 24) -> Optional[str]:
        """获取文件的预签名URL"""
        try:
            full_object_name = f"assets/{object_name}"
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=full_object_name,
                expires=expires_in_hours * 3600
            )
            logger.info(f"🔗 文件URL: {url}")
            return url
        except Exception as e:
            logger.error(f"❌ 获取文件URL失败: {e}")
            return None


async def upload_logos():
    """上传logo资源"""
    uploader = AssetUploader()

    # 确保存储桶存在
    if not await uploader.ensure_bucket_exists():
        return False

    # 定义logo文件列表
    logo_files = {
        "logo-data-agent-v4.1-enhanced.svg": "docs/design/logo/DataAgent_V4_1_Logo_Enhanced.svg",
        "logo-data-agent-v4.1-enhanced.png": "docs/design/logo/DataAgent_V4_1_Logo_Enhanced.png",
        "logo-data-agent-v4.1-enhanced@2x.png": "docs/design/logo/DataAgent_V4_1_Logo_Enhanced@2x.png",
    }

    logger.info("🚀 开始上传Logo资源...")

    successful_uploads = []

    for object_name, file_path in logo_files.items():
        full_path = project_root / file_path

        # 特殊元数据
        metadata = {
            "X-Asset-Type": "logo",
            "X-Brand": "data-agent",
            "X-Description": "DataAgent V4.1 Logo - Enhanced Design"
        }

        success = await uploader.upload_file(
            file_path=full_path,
            object_name=object_name,
            metadata=metadata
        )

        if success:
            successful_uploads.append(object_name)

            # 获取并记录预签名URL
            url = await uploader.get_file_url(object_name)
            if url:
                print(f"📎 {object_name}: {url}")

    logger.info(f"✅ Logo上传完成: {len(successful_uploads)}/{len(logo_files)} 个文件")

    return len(successful_uploads) == len(logo_files)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MinIO资源上传脚本")
    parser.add_argument("--type", choices=["logos", "icons", "all"], default="logos",
                       help="上传的资源类型")
    parser.add_argument("--file", help="上传单个文件")
    parser.add_argument("--directory", help="上传整个目录")
    parser.add_argument("--prefix", default="", help="对象前缀")

    args = parser.parse_args()

    try:
        # 初始化上传器
        uploader = AssetUploader()

        # 确保存储桶存在
        if not await uploader.ensure_bucket_exists():
            return 1

        success = True

        if args.file:
            # 上传单个文件
            file_path = Path(args.file)
            success = await uploader.upload_file(file_path)

        elif args.directory:
            # 上传目录
            directory = Path(args.directory)
            await uploader.upload_directory(directory, args.prefix)

        elif args.type == "logos" or args.type == "all":
            # 上传logo
            logo_success = await upload_logos()
            success = success and logo_success

        if success:
            logger.info("🎉 资源上传任务完成")
            return 0
        else:
            logger.error("❌ 资源上传任务失败")
            return 1

    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"❌ 上传过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)