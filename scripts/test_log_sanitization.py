#!/usr/bin/env python3
"""
测试日志脱敏功能
验证敏感信息是否被正确隐藏
"""

import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# 加载.env文件
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.app.core.config_audit import ConfigAuditLogger

def test_sanitization():
    """测试敏感信息脱敏"""
    print("\n" + "="*70)
    print("🔒 日志脱敏功能测试")
    print("="*70)
    
    audit = ConfigAuditLogger()
    
    # 测试用例 - 使用包含敏感关键词的值
    test_cases = [
        ("zhipuai_api_key", "a269b7edd5114c9e9722543797905708.vEPC6wEKar0N4vMH", "智谱API密钥"),
        ("database_password", "super_secret_pass123", "数据库密码"),
        ("access_token", "bearer_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "访问令牌"),
        ("minio_secret_key", "minio_secret_12345", "MinIO密钥"),
        ("jwt_token", "jwt_1234567890abcdef", "JWT令牌"),
        ("normal_value", "just_a_normal_value", "普通值"),
        ("app_name", "Data Agent Backend", "应用名称"),
    ]
    
    print("\n测试结果:")
    print("-" * 70)
    
    for key, value, description in test_cases:
        sanitized = audit._sanitize_value(value)
        is_redacted = "REDACTED" in str(sanitized)
        status = "✅ 已脱敏" if is_redacted else "⚠️  未脱敏"
        
        print(f"\n{description} ({key}):")
        print(f"  原始值: {value[:20]}...")
        print(f"  脱敏后: {sanitized}")
        print(f"  状态: {status}")
    
    print("\n" + "="*70)
    print("✅ 日志脱敏测试完成")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_sanitization()

