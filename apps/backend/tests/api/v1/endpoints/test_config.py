"""
配置验证 API 端点集成测试

测试 /api/v1/config 路由下的所有端点
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.app.main import app


class TestConfigEndpoints:
    """配置验证端点测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    # ========== GET /config/health 测试 ==========

    def test_config_health_check_success(self, client):
        """测试配置健康检查 - 成功"""
        response = client.get("/api/v1/config/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["service"] == "config_validator"

    # ========== GET /config/status 测试 ==========

    def test_get_config_status_success(self, client):
        """测试获取配置状态 - 成功"""
        response = client.get("/api/v1/config/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "config" in data
        config = data["config"]
        assert "database_configured" in config
        assert "zhipu_configured" in config
        assert "minio_configured" in config
        assert "chromadb_configured" in config

    # ========== GET /config/services 测试 ==========

    def test_get_supported_services_success(self, client):
        """测试获取支持的服务列表 - 成功"""
        response = client.get("/api/v1/config/services")
        
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "total" in data
        assert data["total"] == len(data["services"])
        
        # 验证包含预期的服务
        service_names = [s["name"] for s in data["services"]]
        expected_services = ["database", "minio", "chromadb", "zhipu", "env"]
        for expected in expected_services:
            assert expected in service_names

    # ========== GET /config/validate 测试 ==========

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_validate_all_configs_success(self, mock_validator, client):
        """测试验证所有配置 - 成功"""
        # Mock 验证器返回值
        mock_validator.validate_all_configs = AsyncMock(return_value={
            "overall_status": "success",
            "total_services": 5,
            "successful": 5,
            "failed": 0,
            "timestamp": 1234567890.0,
            "results": []
        })
        
        response = client.get("/api/v1/config/validate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "success"
        assert data["total_services"] == 5
        assert data["successful"] == 5
        assert data["failed"] == 0

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_validate_all_configs_partial_failure(self, mock_validator, client):
        """测试验证所有配置 - 部分失败"""
        mock_validator.validate_all_configs = AsyncMock(return_value={
            "overall_status": "partial_success",
            "total_services": 5,
            "successful": 3,
            "failed": 2,
            "timestamp": 1234567890.0,
            "results": [
                {"service": "database", "status": "success"},
                {"service": "minio", "status": "failed"}
            ]
        })
        
        response = client.get("/api/v1/config/validate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "partial_success"
        assert data["failed"] == 2

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_validate_all_configs_error(self, mock_validator, client):
        """测试验证所有配置 - 异常"""
        mock_validator.validate_all_configs = AsyncMock(
            side_effect=Exception("验证服务不可用")
        )
        
        response = client.get("/api/v1/config/validate")
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower() or "错误" in response.json()["detail"]

    # ========== POST /config/validate 测试 ==========

    def test_validate_specific_service_missing_name(self, client):
        """测试验证特定服务 - 缺少服务名称"""
        response = client.post(
            "/api/v1/config/validate",
            json={"skip_detailed_checks": False}
        )
        
        assert response.status_code == 400
        assert "服务名称" in response.json()["detail"] or "service" in response.json()["detail"].lower()

    def test_validate_specific_service_unsupported(self, client):
        """测试验证特定服务 - 不支持的服务名称"""
        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "unknown_service"}
        )

        assert response.status_code == 400
        assert "不支持" in response.json()["detail"] or "unsupported" in response.json()["detail"].lower()

    @patch("src.app.api.v1.endpoints.config.validate_database")
    def test_validate_database_service_success(self, mock_validate, client):
        """测试验证数据库服务 - 成功"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "service": "database",
            "status": "success",
            "message": "数据库连接正常",
            "details": {},
            "timestamp": 1234567890.0
        }
        mock_validate.return_value = mock_result

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "database"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "database"
        assert data["status"] == "success"

    @patch("src.app.api.v1.endpoints.config.validate_minio")
    def test_validate_minio_service_success(self, mock_validate, client):
        """测试验证MinIO服务 - 成功"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "service": "minio",
            "status": "success",
            "message": "MinIO连接正常",
            "details": {},
            "timestamp": 1234567890.0
        }
        mock_validate.return_value = mock_result

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "minio"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "minio"
        assert data["status"] == "success"

    @patch("src.app.api.v1.endpoints.config.validate_chromadb")
    def test_validate_chromadb_service_success(self, mock_validate, client):
        """测试验证ChromaDB服务 - 成功"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "service": "chromadb",
            "status": "success",
            "message": "ChromaDB连接正常",
            "details": {},
            "timestamp": 1234567890.0
        }
        mock_validate.return_value = mock_result

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "chromadb"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "chromadb"
        assert data["status"] == "success"

    @patch("src.app.api.v1.endpoints.config.validate_zhipu")
    def test_validate_zhipu_service_success(self, mock_validate, client):
        """测试验证智谱AI服务 - 成功"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "service": "zhipu",
            "status": "success",
            "message": "智谱AI API正常",
            "details": {},
            "timestamp": 1234567890.0
        }
        mock_validate.return_value = mock_result

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "zhipu"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "zhipu"
        assert data["status"] == "success"

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_validate_env_service_success(self, mock_validator, client):
        """测试验证环境变量 - 成功"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "service": "env",
            "status": "success",
            "message": "环境变量配置正常",
            "details": {},
            "timestamp": 1234567890.0
        }
        mock_validator.validate_required_env_vars = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "env"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "env"
        assert data["status"] == "success"

    @patch("src.app.api.v1.endpoints.config.validate_database")
    def test_validate_service_internal_error(self, mock_validate, client):
        """测试验证服务 - 内部错误"""
        mock_validate.side_effect = Exception("服务验证异常")

        response = client.post(
            "/api/v1/config/validate",
            json={"service_name": "database"}
        )

        assert response.status_code == 500
        assert "错误" in response.json()["detail"] or "error" in response.json()["detail"].lower()

    # ========== POST /config/test/all 测试 ==========

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_test_all_services_success(self, mock_validator, client):
        """测试所有服务快速测试 - 成功"""
        # 创建Mock结果
        mock_results = []
        for service in ["env", "database", "minio", "chromadb", "zhipu"]:
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {
                "service": service,
                "status": "success",
                "message": f"{service}正常"
            }
            mock_results.append(mock_result)

        mock_validator.validate_required_env_vars = AsyncMock(return_value=mock_results[0])
        mock_validator.validate_database_connection = AsyncMock(return_value=mock_results[1])
        mock_validator.validate_minio_connection = AsyncMock(return_value=mock_results[2])
        mock_validator.validate_chromadb_connection = AsyncMock(return_value=mock_results[3])
        mock_validator.validate_zhipu_api = AsyncMock(return_value=mock_results[4])

        response = client.post("/api/v1/config/test/all")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "success"
        assert data["successful"] == 5
        assert data["total"] == 5

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_test_all_services_partial_failure(self, mock_validator, client):
        """测试所有服务快速测试 - 部分失败"""
        mock_success = MagicMock()
        mock_success.to_dict.return_value = {"service": "test", "status": "success", "message": "ok"}

        mock_fail = MagicMock()
        mock_fail.to_dict.return_value = {"service": "fail", "status": "failed", "message": "error"}

        mock_validator.validate_required_env_vars = AsyncMock(return_value=mock_success)
        mock_validator.validate_database_connection = AsyncMock(return_value=mock_success)
        mock_validator.validate_minio_connection = AsyncMock(return_value=mock_fail)
        mock_validator.validate_chromadb_connection = AsyncMock(return_value=mock_success)
        mock_validator.validate_zhipu_api = AsyncMock(return_value=mock_fail)

        response = client.post("/api/v1/config/test/all")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "partial_success"
        assert data["successful"] == 3
        assert data["total"] == 5

    @patch("src.app.api.v1.endpoints.config.config_validator")
    def test_test_all_services_with_exception(self, mock_validator, client):
        """测试所有服务快速测试 - 有服务抛出异常"""
        mock_success = MagicMock()
        mock_success.to_dict.return_value = {"service": "test", "status": "success", "message": "ok"}

        mock_validator.validate_required_env_vars = AsyncMock(return_value=mock_success)
        mock_validator.validate_database_connection = AsyncMock(side_effect=Exception("连接失败"))
        mock_validator.validate_minio_connection = AsyncMock(return_value=mock_success)
        mock_validator.validate_chromadb_connection = AsyncMock(return_value=mock_success)
        mock_validator.validate_zhipu_api = AsyncMock(return_value=mock_success)

        response = client.post("/api/v1/config/test/all")

        assert response.status_code == 200
        data = response.json()
        # 有一个服务抛出异常，会被捕获为error
        assert data["overall_status"] == "partial_success"
        assert data["successful"] == 4
        assert data["total"] == 5

