"""
健康检查端点测试
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """健康检查端点测试类"""

    def test_root_endpoint(self, client: TestClient):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    def test_main_health_check(self, client: TestClient):
        """测试主健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert "version" in data

    def test_api_v1_info(self, client: TestClient):
        """测试API v1信息端点"""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        assert "app_name" in data
        assert "app_version" in data
        assert "status" in data
        assert "timestamp" in data

    def test_detailed_health_check(self, client: TestClient):
        """测试详细健康检查端点"""
        response = client.get("/api/v1/health/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert "version" in data

        # 检查服务状态结构
        services = data["services"]
        assert "database" in services
        assert "minio" in services
        assert "chromadb" in services
        assert "zhipu_ai" in services

        # 检查每个服务的状态结构
        for service_name, service_info in services.items():
            assert "status" in service_info
            assert "details" in service_info

    def test_ping_endpoint(self, client: TestClient):
        """测试ping端点"""
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
        assert "timestamp" in data

    def test_services_status(self, client: TestClient):
        """测试服务状态端点"""
        response = client.get("/api/v1/health/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "timestamp" in data

        # 检查服务信息结构
        services = data["services"]
        assert "minio" in services
        assert "chromadb" in services
        assert "zhipu_ai" in services

    def test_database_health_check(self, client: TestClient):
        """测试数据库健康检查端点"""
        response = client.get("/api/v1/health/database")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "connection" in data
        assert "details" in data
        assert "timestamp" in data

    def test_health_check_response_structure(self, client: TestClient):
        """测试健康检查响应结构的完整性"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # 验证必需字段存在
        required_fields = ["status", "services", "timestamp", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # 验证状态值
        assert data["status"] in ["healthy", "unhealthy"]

        # 验证服务状态
        services = data["services"]
        expected_services = ["database", "minio", "chromadb", "zhipu_ai"]
        for service in expected_services:
            assert service in services, f"Missing service status: {service}"

        # 验证时间戳格式（ISO 8601）
        timestamp = data["timestamp"]
        assert "T" in timestamp and "Z" in timestamp or "+" in timestamp