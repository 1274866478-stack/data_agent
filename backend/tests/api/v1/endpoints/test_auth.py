"""
认证API端点集成测试 - auth.py
测试所有认证相关的API端点功能
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.app.main import app
from src.app.data.models import Tenant, TenantStatus
from src.app.core.auth import get_current_user_with_tenant, get_current_user_optional


class TestAuthEndpoints:
    """认证API端点测试类"""

    @pytest.fixture
    def mock_user(self):
        """模拟认证用户"""
        user = MagicMock()
        user.id = "user_test_123"
        user.tenant_id = "tenant_test_123"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_verified = True
        user.created_at = "2025-01-01T00:00:00Z"
        return user

    @pytest.fixture
    def mock_tenant(self):
        """模拟租户对象"""
        tenant = MagicMock(spec=Tenant)
        tenant.id = "tenant_test_123"
        tenant.email = "test@example.com"
        tenant.created_at = datetime(2025, 1, 1, 0, 0, 0)
        tenant.status = TenantStatus.ACTIVE
        return tenant

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def authenticated_client(self, mock_user):
        """创建带认证的测试客户端"""
        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user_with_tenant] = override_get_current_user
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    # ==================== POST /auth/verify 测试 ====================

    @patch('src.app.api.v1.endpoints.auth.validate_clerk_token')
    @patch('src.app.api.v1.endpoints.auth.get_token_expiration')
    def test_verify_token_success(self, mock_expiration, mock_validate, client):
        """测试Token验证成功"""
        mock_validate.return_value = {
            "user_id": "user_123",
            "tenant_id": "tenant_123",
            "email": "test@example.com"
        }
        mock_expiration.return_value = datetime.now() + timedelta(hours=1)

        response = client.post(
            "/api/v1/auth/verify",
            json={"token": "valid_jwt_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_info"]["user_id"] == "user_123"
        assert data["expires_at"] is not None

    @patch('src.app.api.v1.endpoints.auth.validate_clerk_token')
    def test_verify_token_invalid(self, mock_validate, client):
        """测试Token验证失败 - 无效token"""
        from src.app.core.jwt_utils import JWTValidationError
        mock_validate.side_effect = JWTValidationError("Invalid token signature")

        response = client.post(
            "/api/v1/auth/verify",
            json={"token": "invalid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Invalid token signature" in data["error_message"]

    def test_verify_token_missing_token(self, client):
        """测试Token验证 - 缺少token字段"""
        response = client.post(
            "/api/v1/auth/verify",
            json={}
        )

        assert response.status_code == 422  # Validation error

    # ==================== GET /auth/me 测试 ====================

    def test_get_current_user_success(self, authenticated_client):
        """测试获取当前用户信息成功"""
        response = authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user_test_123"
        assert data["tenant_id"] == "tenant_test_123"
        assert data["email"] == "test@example.com"

    def test_get_current_user_unauthenticated(self, client):
        """测试获取当前用户信息 - 未认证"""
        response = client.get("/api/v1/auth/me")
        # 未认证时应返回401
        assert response.status_code == 401

    # ==================== GET /auth/tenant 测试 ====================

    def test_get_tenant_info_existing(self, mock_user, mock_tenant):
        """测试获取租户信息 - 租户已存在"""
        from src.app.data.database import get_db

        def override_get_current_user():
            return mock_user

        def override_get_db():
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_tenant
            yield mock_db

        app.dependency_overrides[get_current_user_with_tenant] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        response = client.get("/api/v1/auth/tenant")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant_test_123"
        assert data["status"] == "active"

    # ==================== GET /auth/status 测试 ====================

    def test_get_auth_status_authenticated(self):
        """测试获取认证状态 - 已认证"""
        user_info = {
            "user_id": "user_123",
            "tenant_id": "tenant_123",
            "email": "test@example.com",
            "is_verified": True
        }

        def override_get_user_optional():
            return user_info

        app.dependency_overrides[get_current_user_optional] = override_get_user_optional
        client = TestClient(app)
        response = client.get("/api/v1/auth/status")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["user_id"] == "user_123"

    def test_get_auth_status_not_authenticated(self):
        """测试获取认证状态 - 未认证"""
        def override_get_user_optional():
            return None

        app.dependency_overrides[get_current_user_optional] = override_get_user_optional
        client = TestClient(app)
        response = client.get("/api/v1/auth/status")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user"] is None

    # ==================== POST /auth/logout 测试 ====================

    def test_logout_success(self, authenticated_client):
        """测试用户登出成功"""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
        assert "timestamp" in data

    # ==================== GET /auth/config 测试 ====================

    def test_get_auth_config_success(self, client):
        """测试获取认证配置成功"""
        response = client.get("/api/v1/auth/config")

        assert response.status_code == 200
        data = response.json()
        assert data["auth_provider"] == "clerk"
        assert "jwt_issuer" in data
        assert "supported_flows" in data
        assert data["token_validation"] == "enabled"
        assert data["tenant_isolation"] == "enabled"

    # ==================== POST /auth/refresh-tenant 测试 ====================

    def test_refresh_tenant_create_new(self, mock_user):
        """测试刷新租户 - 创建新租户"""
        from src.app.data.database import get_db

        def override_get_current_user():
            return mock_user

        def override_get_db():
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            yield mock_db

        app.dependency_overrides[get_current_user_with_tenant] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        response = client.post("/api/v1/auth/refresh-tenant")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["tenant_id"] == "tenant_test_123"

    def test_refresh_tenant_existing(self, mock_user, mock_tenant):
        """测试刷新租户 - 租户已存在"""
        from src.app.data.database import get_db

        # 设置email属性
        mock_user.email = "test@example.com"
        mock_tenant.email = "test@example.com"

        def override_get_current_user():
            return mock_user

        def override_get_db():
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_tenant
            yield mock_db

        app.dependency_overrides[get_current_user_with_tenant] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        response = client.post("/api/v1/auth/refresh-tenant")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "existing"
        assert "Tenant already exists" in data["message"]

    # ==================== POST /auth/test-token 测试 ====================

    @patch('src.app.api.v1.endpoints.auth.get_current_user_optional')
    @patch('src.app.api.v1.endpoints.auth.validate_clerk_token')
    @patch('src.app.api.v1.endpoints.auth.get_token_expiration')
    def test_test_token_validation_success(self, mock_expiration, mock_validate, mock_get_user, client):
        """测试Token验证功能 - 成功"""
        mock_get_user.return_value = None
        mock_validate.return_value = {"user_id": "user_123", "tenant_id": "tenant_123"}
        mock_expiration.return_value = datetime.now() + timedelta(hours=1)

        response = client.post(
            "/api/v1/auth/test-token",
            params={"token": "test_jwt_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_info"]["user_id"] == "user_123"

    @patch('src.app.api.v1.endpoints.auth.get_current_user_optional')
    @patch('src.app.api.v1.endpoints.auth.validate_clerk_token')
    def test_test_token_validation_invalid(self, mock_validate, mock_get_user, client):
        """测试Token验证功能 - 无效token"""
        from src.app.core.jwt_utils import JWTValidationError
        mock_get_user.return_value = None
        mock_validate.side_effect = JWTValidationError("Token expired")

        response = client.post(
            "/api/v1/auth/test-token",
            params={"token": "expired_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Token expired" in data["error_message"]

    # ==================== 边界条件测试 ====================

    def test_verify_token_empty_token(self, client):
        """测试Token验证 - 空token"""
        response = client.post(
            "/api/v1/auth/verify",
            json={"token": ""}
        )

        # 空字符串也会尝试验证，应该返回200但valid=False
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    @patch('src.app.api.v1.endpoints.auth.validate_clerk_token')
    def test_verify_token_internal_error(self, mock_validate, client):
        """测试Token验证 - 内部错误"""
        mock_validate.side_effect = Exception("Unexpected error")

        response = client.post(
            "/api/v1/auth/verify",
            json={"token": "some_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Internal server error" in data["error_message"]

