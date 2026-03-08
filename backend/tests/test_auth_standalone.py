"""
Standalone Self-Hosted Authentication Tests

直接测试认证逻辑，不依赖完整应用
"""

import sys
import os

# 添加 src 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, timedelta
from passlib.context import CryptContext
import base64
import json
import hmac
import hashlib


def test_password_hashing():
    """测试密码哈希"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    password = "test_password_123"
    hash_result = pwd_context.hash(password)

    print(f"✓ 密码哈希测试通过")
    print(f"  原始密码: {password}")
    print(f"  哈希结果: {hash_result[:40]}...")

    # 验证特征
    assert hash_result.startswith("$2b$")
    assert len(hash_result) == 60

    # 验证功能
    assert pwd_context.verify(password, hash_result) is True
    assert pwd_context.verify("wrong_password", hash_result) is False

    print(f"  ✓ 密码验证通过")
    return True


def test_jwt_generation():
    """测试 JWT token 生成"""
    secret_key = "test-secret-key-for-jwt-signing"
    user_id = "test-user-123"
    email = "test@example.com"
    tenant_id = "test-tenant-456"

    # 构造 payload
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "iat": now.timestamp(),
        "exp": (now + timedelta(days=7)).timestamp(),
    }

    # 简化的 JWT 编码（用于测试）
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=')

    message = header_b64 + b'.' + payload_b64
    signature = hmac.new(secret_key.encode(), message, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=')

    token = message + b'.' + signature_b64

    print(f"✓ JWT Token 生成测试通过")
    print(f"  Token: {token[:50]}...")

    parts = token.split(b'.')
    assert len(parts) == 3

    # 解码验证
    decoded_payload = json.loads(base64.urlsafe_b64decode(parts[1] + b'=='))
    assert decoded_payload['sub'] == user_id
    assert decoded_payload['email'] == email
    assert decoded_payload['tenant_id'] == tenant_id

    print(f"  ✓ Payload 解码验证通过")
    return True


def test_email_validation():
    """测试邮箱验证"""
    from pydantic import BaseModel, EmailStr, ValidationError

    class RegisterRequest(BaseModel):
        email: EmailStr
        password: str

    # 有效邮箱
    valid = RegisterRequest(email="user@example.com", password="SecurePass123!")
    assert valid.email == "user@example.com"
    print(f"✓ 邮箱验证测试通过")

    # 无效邮箱应该抛出错误
    try:
        RegisterRequest(email="invalid-email", password="pass123")
        assert False, "应该抛出 ValidationError"
    except ValidationError:
        print(f"  ✓ 无效邮箱正确拒绝")

    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("自托管认证功能测试")
    print("=" * 50)

    tests = [
        ("密码哈希", test_password_hashing),
        ("JWT Token 生成", test_jwt_generation),
        ("邮箱验证", test_email_validation),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n【{name}】")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
