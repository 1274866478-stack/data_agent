#!/usr/bin/env python3
"""
MinIO连接测试脚本
用于测试连接和创建存储桶
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

# 从.env文件加载环境变量
def load_env():
    """加载.env文件中的环境变量"""
    env_file = project_root / ".env"
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
    """测试MinIO连接"""

    # 加载环境变量
    load_env()

    print("MinIO连接测试")
    print("=" * 30)

    # 显示当前配置
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    root_user = os.getenv("MINIO_ROOT_USER", "")
    root_password = os.getenv("MINIO_ROOT_PASSWORD", "")
    bucket_name = os.getenv("MINIO_BUCKET_NAME", "dataagent-files")

    print(f"端点: {endpoint}")
    print(f"用户: {root_user[:10]}..." if root_user else "用户: (空)")
    print(f"密码: {'*' * len(root_password)}" if root_password else "密码: (空)")
    print(f"存储桶: {bucket_name}")
    print()

    try:
        from minio import Minio
        from minio.error import S3Error

        # 创建客户端
        client = Minio(
            endpoint=endpoint,
            access_key=root_user,
            secret_key=root_password,
            secure=False
        )

        print("[OK] MinIO客户端创建成功")

        # 测试连接 - 列出存储桶
        buckets = client.list_buckets()
        print(f"[OK] 连接成功，发现 {len(buckets)} 个存储桶:")
        for bucket in buckets:
            print(f"   - {bucket.name}")

        # 检查目标存储桶
        if bucket_name in [b.name for b in buckets]:
            print(f"[OK] 存储桶 '{bucket_name}' 已存在")
        else:
            print(f"[INFO] 存储桶 '{bucket_name}' 不存在，将尝试创建...")
            client.make_bucket(bucket_name)
            print(f"[OK] 存储桶 '{bucket_name}' 创建成功")

        return True

    except ImportError:
        print("[ERROR] 缺少minio库，请安装: pip install minio")
        return False
    except S3Error as e:
        print(f"[ERROR] MinIO操作失败: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 连接测试失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)