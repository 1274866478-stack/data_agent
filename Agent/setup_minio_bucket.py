"""
创建 mcp-echarts 专用的 MinIO bucket
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取 MinIO 配置
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

BUCKET_NAME = "mcp-echarts"

def main():
    print(f"MinIO Endpoint: {MINIO_ENDPOINT}")
    print(f"Access Key: {MINIO_ACCESS_KEY[:10]}...")
    print(f"Secure: {MINIO_SECURE}")
    print(f"Bucket: {BUCKET_NAME}")
    print()
    
    try:
        from minio import Minio
        import json

        # minio 7.2+ API: 所有参数都是关键字参数
        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )

        # 检查 bucket 是否存在
        found = client.bucket_exists(bucket_name=BUCKET_NAME)
        if not found:
            client.make_bucket(bucket_name=BUCKET_NAME)
            print(f"[OK] Bucket '{BUCKET_NAME}' created")
        else:
            print(f"[OK] Bucket '{BUCKET_NAME}' already exists")

        # 设置 bucket 策略为公开读取
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"]
            }]
        }
        client.set_bucket_policy(bucket_name=BUCKET_NAME, policy=json.dumps(policy))
        print(f"[OK] Bucket policy set for public read")

        # 列出所有 bucket
        print("\nAll buckets:")
        for bucket in client.list_buckets():
            print(f"  - {bucket.name}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

