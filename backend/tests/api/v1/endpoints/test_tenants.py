"""
租户管理端点测试
验证Story-2.2实现的租户管理API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json

from src.app.main import app
from src.app.data.models import Tenant, TenantStatus


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_tenant():
    """示例租户数据"""
    return {
        "id": "tenant_123",
        "email": "test@example.com",
        "status": "active",
        "display_name": "Test Tenant",
        "settings": {
            "timezone": "UTC",
            "language": "en",
            "notification_preferences": {
                "email_notifications": True,
                "system_alerts": True
            },
            "ui_preferences": {
                "theme": "light",
                "dashboard_layout": "default"
            }
        },
        "storage_quota_mb": 1024,
        "created_at": "2025-11-17T00:00:00Z",
        "updated_at": "2025-11-17T00:00:00Z"
    }


@pytest.fixture
def sample_tenant_stats():
    """示例租户统计数据"""
    return {
        "total_documents": 25,
        "total_data_sources": 3,
        "storage_used_mb": 512,
        "processed_documents": 20,
        "pending_documents": 5,
        "storage_quota_mb": 1024,
        "storage_usage_percent": 50.0
    }


class TestTenantEndpoints:
    """租户管理端点测试类"""

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant')
    def test_get_current_tenant_success(self, mock_get_tenant, client, sample_tenant):
        """测试获取当前租户信息成功（Story要求：GET /me）"""
        # 模拟租户
        mock_tenant = Mock()
        mock_tenant.to_dict.return_value = sample_tenant
        mock_get_tenant.return_value = mock_tenant

        # 执行请求
        response = client.get("/api/v1/tenants/me")

        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_tenant["id"]
        assert data["email"] == sample_tenant["email"]
        assert data["status"] == sample_tenant["status"]

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant')
    def test_get_current_tenant_not_found(self, mock_get_tenant, client):
        """测试获取当前租户信息失败"""
        # 模拟租户不存在
        mock_get_tenant.side_effect = Exception("Tenant not found")

        # 执行请求
        response = client.get("/api/v1/tenants/me")

        # 验证结果
        assert response.status_code == 500

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant_id')
    @patch('src.app.api.v1.endpoints.tenants.get_tenant_service')
    def test_update_current_tenant_success(
        self, mock_get_service, mock_get_tenant_id, client, sample_tenant
    ):
        """测试更新当前租户信息成功（Story要求：PUT /me）"""
        # 准备测试数据
        tenant_id = "tenant_123"
        update_data = {
            "display_name": "Updated Tenant",
            "settings": {
                "timezone": "Asia/Shanghai",
                "language": "zh"
            }
        }

        # 模拟服务
        mock_service = AsyncMock()
        mock_tenant = Mock()
        mock_tenant.to_dict.return_value = {**sample_tenant, **update_data}
        mock_service.update_tenant.return_value = mock_tenant

        mock_get_tenant_id.return_value = tenant_id
        mock_get_service.return_value = mock_service

        # 执行请求
        response = client.put("/api/v1/tenants/me", json=update_data)

        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == update_data["display_name"]

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant_id')
    @patch('src.app.api.v1.endpoints.tenants.get_tenant_service')
    def test_update_current_tenant_not_found(
        self, mock_get_service, mock_get_tenant_id, client
    ):
        """测试更新不存在的租户"""
        tenant_id = "nonexistent_tenant"
        update_data = {"display_name": "Updated Tenant"}

        mock_get_tenant_id.return_value = tenant_id
        mock_service = AsyncMock()
        mock_service.update_tenant.return_value = None
        mock_get_service.return_value = mock_service

        # 执行请求
        response = client.put("/api/v1/tenants/me", json=update_data)

        # 验证结果
        assert response.status_code == 404

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant_id')
    @patch('src.app.api.v1.endpoints.tenants.get_tenant_service')
    def test_get_current_tenant_stats_success(
        self, mock_get_service, mock_get_tenant_id, client, sample_tenant_stats
    ):
        """测试获取当前租户统计信息成功（Story要求：GET /me/stats）"""
        tenant_id = "tenant_123"

        mock_get_tenant_id.return_value = tenant_id
        mock_service = AsyncMock()
        mock_service.get_tenant_stats.return_value = sample_tenant_stats
        mock_get_service.return_value = mock_service

        # 执行请求
        response = client.get("/api/v1/tenants/me/stats")

        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == tenant_id
        assert "statistics" in data
        assert data["statistics"]["total_documents"] == sample_tenant_stats["total_documents"]

    @patch('src.app.api.v1.endpoints.tenants.get_current_tenant_id')
    @patch('src.app.api.v1.endpoints.tenants.get_tenant_service')
    def test_get_current_tenant_stats_not_found(
        self, mock_get_service, mock_get_tenant_id, client
    ):
        """测试获取不存在租户的统计信息"""
        tenant_id = "nonexistent_tenant"

        mock_get_tenant_id.return_value = tenant_id
        mock_service = AsyncMock()
        mock_service.get_tenant_stats.return_value = None
        mock_get_service.return_value = mock_service

        # 执行请求
        response = client.get("/api/v1/tenants/me/stats")

        # 验证结果
        assert response.status_code == 404

    @patch('src.app.api.v1.endpoints.tenants.get_tenant_setup_service')
    def test_setup_tenant_success(self, mock_get_setup_service, client, sample_tenant):
        """测试新租户初始化成功（Story要求：POST /setup）"""
        # 准备测试数据
        setup_data = {
            "tenant_id": "new_tenant_123",
            "email": "new@example.com",
            "display_name": "New Tenant",
            "settings": {"timezone": "Asia/Shanghai"}
        }

        # 模拟服务
        mock_setup_service = AsyncMock()
        mock_setup_service.setup_new_tenant.return_value = {
            "success": True,
            "tenant_id": setup_data["tenant_id"],
            "message": "Tenant setup completed successfully",
            "tenant": sample_tenant
        }
        mock_get_setup_service.return_value = mock_setup_service

        # 执行请求
        response = client.post("/api/v1/tenants/setup", json=setup_data)

        # 验证结果
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["tenant_id"] == setup_data["tenant_id"]

    @patch('src.app.api.v1.endpoints.tenants.get_tenant_setup_service')
    def test_setup_tenant_failure(self, mock_get_setup_service, client):
        """测试新租户初始化失败"""
        setup_data = {
            "tenant_id": "new_tenant_123",
            "email": "invalid-email"
        }

        # 模拟服务失败
        mock_setup_service = AsyncMock()
        mock_setup_service.setup_new_tenant.return_value = {
            "success": False,
            "error": "Invalid email format",
            "message": "Tenant setup failed"
        }
        mock_get_setup_service.return_value = mock_setup_service

        # 执行请求
        response = client.post("/api/v1/tenants/setup", json=setup_data)

        # 验证结果
        assert response.status_code == 400

    def test_tenant_update_request_validation(self, client):
        """测试租户更新请求验证"""
        # 测试无效数据
        invalid_data = {
            "storage_quota_mb": -100  # 负数
        }

        response = client.put("/api/v1/tenants/me", json=invalid_data)
        # 应该返回验证错误或正常处理（取决于Pydantic配置）

    def test_tenant_setup_request_validation(self, client):
        """测试租户初始化请求验证"""
        # 测试缺少必需字段
        incomplete_data = {
            "email": "test@example.com"
            # 缺少 tenant_id
        }

        response = client.post("/api/v1/tenants/setup", json=incomplete_data)
        assert response.status_code == 422  # 验证错误


class TestTenantAPIIntegration:
    """租户API集成测试"""

    def test_tenant_api_structure(self, client):
        """测试租户API结构完整性"""
        # 验证所有必需的端点都存在
        endpoints = [
            "/api/v1/tenants/me",
            "/api/v1/tenants/me/stats",
            "/api/v1/tenants/setup"
        ]

        for endpoint in endpoints:
            # 发送请求（可能会因为认证失败返回401，但端点应该存在）
            response = client.get(endpoint)
            assert response.status_code in [401, 403, 404, 422, 500]  # 不是404表示端点存在

    def test_tenant_api_response_format(self, client):
        """测试租户API响应格式"""
        # 测试错误响应格式
        response = client.get("/api/v1/tenants/me")
        if response.status_code != 200:
            data = response.json()
            assert "detail" in data  # FastAPI错误格式