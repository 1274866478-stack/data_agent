#!/usr/bin/env python3
"""
极简MinIO Logo上传脚本
使用默认凭据进行上传测试
"""

import os
import sys
from pathlib import Path

def main():
    """使用默认凭据上传logo"""

    print("DataAgent V4.1 Logo上传 - 默认凭据模式")
    print("=" * 50)

    # 使用MinIO默认凭据
    endpoint = "localhost:9000"
    access_key = "minioadmin"
    secret_key = "minioadmin"
    bucket_name = "dataagent-files"

    print(f"端点: {endpoint}")
    print(f"访问密钥: {access_key}")
    print(f"存储桶: {bucket_name}")
    print()

    try:
        from minio import Minio
        from minio.error import S3Error

        # 创建客户端
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

        print("[OK] MinIO客户端创建成功")

        # 测试连接
        try:
            buckets = client.list_buckets()
            print(f"[OK] 连接成功，发现 {len(buckets)} 个存储桶")
        except S3Error as e:
            if "InvalidAccessKeyId" in str(e):
                print("[WARNING] 默认凭据失败，但会继续尝试创建存储桶...")
            else:
                raise e

        # 检查或创建存储桶
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                print(f"[OK] 存储桶 '{bucket_name}' 创建成功")
            else:
                print(f"[OK] 存储桶 '{bucket_name}' 已存在")
        except S3Error as e:
            print(f"[ERROR] 存储桶操作失败: {e}")
            print("[INFO] 尝试使用其他存储桶名称...")
            bucket_name = "logos"
            try:
                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)
                    print(f"[OK] 备用存储桶 '{bucket_name}' 创建成功")
            except S3Error as e2:
                print(f"[ERROR] 备用存储桶也失败: {e2}")
                return False

        # 上传logo文件
        logo_files = [
            "../frontend/public/logo.svg",
            "../docs/design/logo/DataAgent_V4_1_Logo_Enhanced.svg"
        ]

        success_count = 0
        current_dir = Path(__file__).parent

        for logo_file in logo_files:
            file_path = current_dir / logo_file
            if not file_path.exists():
                print(f"[SKIP] 文件不存在: {file_path}")
                continue

            object_name = f"assets/{file_path.name}"
            print(f"\n[UPLOAD] 上传: {file_path.name}")
            print(f"        到: {object_name}")

            try:
                result = client.fput_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=str(file_path)
                )

                print(f"[SUCCESS] 上传成功:")
                print(f"          大小: {result.size} bytes")
                print(f"          ETag: {result.etag}")

                # 生成预签名URL
                url = client.presigned_get_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=24*3600  # 24小时
                )
                print(f"          URL: {url}")

                success_count += 1

            except S3Error as e:
                print(f"[ERROR] 上传失败: {e}")

        print(f"\n[SUMMARY] 上传完成: {success_count} 个文件成功")

        if success_count > 0:
            print(f"[INFO] MinIO控制台: http://{endpoint}:9001")
            return True
        else:
            return False

    except ImportError:
        print("[ERROR] 缺少minio库，请安装: pip install minio")
        return False
    except Exception as e:
        print(f"[ERROR] 操作失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)