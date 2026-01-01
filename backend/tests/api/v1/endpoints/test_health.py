"""
[HEADER]
健康检查端点测试 - Health Endpoints Tests
验证健康检查API端点的功能和响应格式

[MODULE]
模块类型: API端点测试 (Endpoint Tests)
所属功能: 健康检查API测试
技术栈: pytest, FastAPI TestClient

[INPUT]
- 依赖的Fixtures:
  - client (TestClient): FastAPI测试客户端
    - 从 conftest.py 或其他地方导入
    - 自动处理HTTP请求和响应
- 测试数据:
  - 无需额外测试数据
  - 使用实际API端点

[OUTPUT]
- 测试覆盖:
  1. test_root_endpoint: 测试根路径 (/)
  2. test_main_health_check: 测试主健康检查 (/health)
  3. test_api_v1_info: 测试API v1信息 (/api/v1/)
  4. test_detailed_health_check: 测试详细健康检查 (/api/v1/health/status)
  5. test_database_health: 测试数据库健康检查 (/api/v1/health/database)
  6. test_services_health: 测试服务状态检查 (/api/v1/health/services)
- 断言验证:
  - HTTP状态码 (200, 201等)
  - 响应JSON结构
  - 必需字段存在性
  - 数据类型正确性

[LINK]
- 测试目标:
  - src.app.api.v1.endpoints.health - 健康检查端点实现
  - src.app.main - FastAPI应用路由
- 依赖测试:
  - tests/conftest.py - 测试配置和fixtures
- 关联API:
  - GET / - 根路径
  - GET /health - 主健康检查
  - GET /api/v1/ - API信息
  - GET /api/v1/health/status - 详细健康状态
  - GET /api/v1/health/database - 数据库健康
  - GET /api/v1/health/services - 服务状态

[POS]
- 文件路径: backend/tests/api/v1/endpoints/test_health.py
- 测试类别: 集成测试 (API端点测试)
- 执行顺序: 可独立运行, 无依赖
- 运行方式:
  - 单独运行: pytest tests/api/v1/endpoints/test_health.py
  - 套件运行: pytest tests/api/v1/endpoints/
  - 全部运行: pytest tests/

[PROTOCOL]
- 测试结构:
  - 使用类组织: TestHealthEndpoints
  - 每个端点一个测试方法
  - 测试方法命名: test_<endpoint>_<functionality>
- 断言策略:
  1. 状态码断言: assert response.status_code == 200
  2. 响应数据: data = response.json()
  3. 字段存在: assert "field" in data
  4. 值验证: assert data["field"] == expected
- 响应格式验证:
  - 根路径: {message, version, docs, health}
  - 健康检查: {status, services, timestamp, version}
  - API信息: {api_version, app_name, app_version, status, timestamp}
- 测试隔离:
  - 每个测试独立运行
  - 无共享状态
  - 不依赖测试执行顺序

[TEST_CASES]
- test_root_endpoint:
  - 端点: GET /
  - 验证: 状态码200, 包含message/version/docs/health字段
- test_main_health_check:
  - 端点: GET /health
  - 验证: 状态码200, 包含status/services/timestamp/version
- test_api_v1_info:
  - 端点: GET /api/v1/
  - 验证: 状态码200, api_version=="v1", 包含app信息
- test_detailed_health_check:
  - 端点: GET /api/v1/health/status
  - 验证: 状态码200, 包含status/services/timestamp
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