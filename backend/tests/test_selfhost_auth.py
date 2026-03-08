"""
Self-Hosted Authentication Unit Tests

测试自托管认证的核心逻辑：
1. 密码哈希和验证
2. JWT token 生成和验证
3. 注册/登录请求模型
"""

import pytest
from datetime import datetime, timedelta
from passlib.context import CryptContext


class TestPasswordHashing:
    """测试密码哈希功能"""

    def setUp(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def test_password_hashing(self):
        """测试密码哈希生成"""
        password = "test_password_123"
        hash_result = self.pwd_context.hash(password)

        # 验证哈希值特征
        assert hash_result.startswith("$2b$")  # bcrypt 哈希前缀
        assert len(hash_result) == 60  # bcrypt 标准长度
        assert hash_result != password  # 哈希值不等于明文

    def test_password_verification(self):
        """测试密码验证"""
        password = "test_password_123"
        hash_result = self.pwd_context.hash(password)

        # 正确密码应该验证通过
        assert self.pwd_context.verify(password, hash_result) is True

        # 错误密码应该验证失败
        assert self.pwd_context.verify("wrong_password", hash_result) is False


class TestJWTGeneration:
    """测试 JWT token 生成"""

    def test_jwt_token_structure(self):
        """测试 JWT token 结构"""
        from src.app.core.jwt_utils import create_selfhost_jwt

        secret_key = "test-secret-key-for-jwt-signing"
        user_id = "test-user-123"
        email = "test@example.com"
        tenant_id = "test-tenant-456"

        token = create_selfhost_jwt(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            secret_key=secret_key,
            expires_delta=timedelta(hours=24)
        )

        # JWT 格式: header.payload.signature
        parts = token.split('.')
        assert len(parts) == 3

        # 验证 token 包含必要信息
        import base64
        import json

        # 解码 payload
        payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        assert payload['sub'] == user_id
        assert payload['email'] == email
        assert payload['tenant_id'] == tenant_id
        assert 'exp' in payload


class TestAuthModels:
    """测试认证请求/响应模型"""

    def test_register_request_validation(self):
        """测试注册请求验证"""
        from src.app.api.v1.endpoints.auth import RegisterRequest
        from pydantic import ValidationError

        # 有效数据
        valid_data = {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "display_name": "Test User"
        }
        request = RegisterRequest(**valid_data)
        assert request.email == "user@example.com"

        # 无效邮箱
        with pytest.raises(ValidationError):
            RegisterRequest(email="invalid-email", password="pass123")

    def test_login_request_validation(self):
        """测试登录请求验证"""
        from src.app.api.v1.endpoints.auth import LoginRequest

        valid_data = {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
        request = LoginRequest(**valid_data)
        assert request.email == "user@example.com"


class TestUserModel:
    """测试 User 数据模型"""

    def test_user_password_methods(self):
        """测试 User 模型的密码方法"""
        from src.app.data.models import User

        # 创建测试用户实例
        user = User(
            id="test-user-123",
            email="test@example.com",
            tenant_id="test-tenant-456"
        )

        # 设置密码
        user.set_password("SecurePass123!")
        assert user.password_hash is not None
        assert user.password_hash != "SecurePass123!"

        # 验证密码
        assert user.verify_password("SecurePass123!") is True
        assert user.verify_password("WrongPassword") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
