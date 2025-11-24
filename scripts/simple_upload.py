#!/usr/bin/env python3
"""
简化的MinIO上传脚本 - 专门用于logo上传
不依赖复杂的后端模块，直接使用minio库
"""

import os
import sys
from pathlib import Path
from minio import Minio
from minio.error import S3Error
import mimetypes

# 从.env文件加载环境变量
def load_env():
    """加载.env文件中的环境变量"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 移除引号
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

def main():
    """上传logo文件到MinIO"""

    # 加载环境变量
    load_env()

    # MinIO配置 - 从环境变量读取
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    # 使用MINIO_ROOT_USER和MINIO_ROOT_PASSWORD作为访问凭据
    MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "VglMp1kuFERnZy0y8ycG6m6icHQa851y")
    MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "hWw%Kn+wr$STk@YQEUTLP%n+2J-KyIGH+GVLYBxfR5cAJO)_AH^-MG^QSwgCub)4")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "dataagent-files")
    MINIO_SECURE = False  # 本地开发不使用HTTPS

    # Logo文件路径
    logo_files = [
        "docs/design/logo/DataAgent_V4_1_Logo_Enhanced.svg",
    ]

    print("DataAgent V4.1 Logo上传工具")
    print("=" * 50)

    try:
        # 创建MinIO客户端
        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )

        print(f"[OK] MinIO客户端创建成功: {MINIO_ENDPOINT}")

        # 检查存储桶是否存在
        if not client.bucket_exists(MINIO_BUCKET_NAME):
            client.make_bucket(MINIO_BUCKET_NAME)
            print(f"[OK] 创建存储桶: {MINIO_BUCKET_NAME}")
        else:
            print(f"[OK] 存储桶已存在: {MINIO_BUCKET_NAME}")

        # 上传每个logo文件
        project_root = Path(__file__).parent.parent
        success_count = 0

        for logo_file in logo_files:
            file_path = project_root / logo_file

            if not file_path.exists():
                print(f"[ERROR] 文件不存在: {file_path}")
                continue

            # 对象名称
            object_name = f"assets/{file_path.name}"

            # 获取MIME类型
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "application/octet-stream"

            # 准备元数据
            metadata = {
                "Content-Type": content_type,
                "X-Project": "data-agent-v4",
                "X-Version": "4.1",
                "X-Asset-Type": "logo",
                "X-Description": "DataAgent V4.1 Enhanced Logo"
            }

            try:
                # 上传文件
                result = client.fput_object(
                    bucket_name=MINIO_BUCKET_NAME,
                    object_name=object_name,
                    file_path=str(file_path),
                    metadata=metadata
                )

                print(f"[OK] 上传成功:")
                print(f"   文件: {file_path.name}")
                print(f"   大小: {result.size} bytes")
                print(f"   对象: {object_name}")

                # 生成预签名URL
                url = client.presigned_get_object(
                    bucket_name=MINIO_BUCKET_NAME,
                    object_name=object_name,
                    expires=24*3600  # 24小时
                )
                print(f"   URL: {url}")

                success_count += 1

            except S3Error as e:
                print(f"[ERROR] 上传失败 {file_path.name}: {e}")

        print(f"\n[STAT] 上传结果: {success_count}/{len(logo_files)} 个文件成功")

        if success_count == len(logo_files):
            print("[SUCCESS] 所有Logo文件上传完成！")
            print(f"[INFO] MinIO控制台: http://{MINIO_ENDPOINT}")
            return 0
        else:
            print("[ERROR] 部分文件上传失败")
            return 1

    except S3Error as e:
        print(f"[ERROR] MinIO操作失败: {e}")
        print("[TIPS] 请检查:")
        print("   1. MinIO服务是否正在运行")
        print("   2. 连接配置是否正确")
        print("   3. 访问密钥是否有效")
        return 1
    except Exception as e:
        print(f"[ERROR] 发生未知错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)