#!/usr/bin/env python3
"""
密钥生成脚本
生成符合安全标准的强随机密钥
"""

import secrets
import string
import argparse
from typing import Dict


def generate_secret_key(length: int = 64) -> str:
    """
    生成SECRET_KEY（用于JWT签名等）
    包含大小写字母、数字和特殊字符
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_minio_access_key(length: int = 32) -> str:
    """
    生成MinIO访问密钥
    包含大小写字母和数字
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_minio_secret_key(length: int = 64) -> str:
    """
    生成MinIO秘密密钥
    包含大小写字母、数字和特殊字符
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key(length: int = 48) -> str:
    """
    生成API密钥
    使用URL安全的字符集
    """
    return secrets.token_urlsafe(length)


def generate_all_keys() -> Dict[str, str]:
    """生成所有需要的密钥"""
    return {
        "SECRET_KEY": generate_secret_key(64),
        "MINIO_ACCESS_KEY": generate_minio_access_key(32),
        "MINIO_SECRET_KEY": generate_minio_secret_key(64),
        "MINIO_ROOT_USER": generate_minio_access_key(32),
        "MINIO_ROOT_PASSWORD": generate_minio_secret_key(64),
    }


def print_keys(keys: Dict[str, str], show_instructions: bool = True):
    """打印生成的密钥"""
    print("\n" + "="*70)
    print("🔑 生成的安全密钥")
    print("="*70)
    
    for key_name, key_value in keys.items():
        print(f"\n{key_name}={key_value}")
    
    print("\n" + "="*70)
    
    if show_instructions:
        print("\n📋 使用说明:")
        print("1. 复制上述密钥到你的 .env 文件")
        print("2. 确保 .env 文件在 .gitignore 中")
        print("3. 不要将密钥提交到版本控制系统")
        print("4. 在生产环境中使用不同的密钥")
        print("5. 定期轮换密钥（建议每90天）")
        print("\n⚠️  警告:")
        print("   - 这些密钥只显示一次，请妥善保存")
        print("   - 不要通过不安全的渠道传输密钥")
        print("   - 如果密钥泄露，立即重新生成")
        print("="*70 + "\n")


def save_to_file(keys: Dict[str, str], filename: str = ".env.generated"):
    """保存密钥到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 自动生成的安全密钥\n")
        f.write(f"# 生成时间: {secrets.token_hex(8)}\n")
        f.write("# 请将这些值复制到你的 .env 文件中\n\n")
        
        for key_name, key_value in keys.items():
            f.write(f"{key_name}={key_value}\n")
    
    print(f"✅ 密钥已保存到: {filename}")
    print(f"⚠️  请在复制后删除此文件！")


def main():
    parser = argparse.ArgumentParser(description="生成安全密钥")
    parser.add_argument(
        "--save",
        action="store_true",
        help="保存密钥到 .env.generated 文件"
    )
    parser.add_argument(
        "--key-type",
        choices=["secret", "minio_access", "minio_secret", "api", "all"],
        default="all",
        help="指定要生成的密钥类型"
    )
    parser.add_argument(
        "--length",
        type=int,
        help="密钥长度（覆盖默认值）"
    )
    
    args = parser.parse_args()
    
    if args.key_type == "all":
        keys = generate_all_keys()
        print_keys(keys)
        
        if args.save:
            save_to_file(keys)
    else:
        # 生成单个密钥
        key_generators = {
            "secret": (generate_secret_key, 64),
            "minio_access": (generate_minio_access_key, 32),
            "minio_secret": (generate_minio_secret_key, 64),
            "api": (generate_api_key, 48)
        }
        
        generator, default_length = key_generators[args.key_type]
        length = args.length if args.length else default_length
        
        key_value = generator(length)
        print(f"\n{args.key_type.upper()}: {key_value}\n")


if __name__ == "__main__":
    main()

