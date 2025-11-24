"""
配置验证模块测试用例
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.app.core.config_validator import (
    ConfigValidator,
    ValidationResult,
    config_validator,
    validate_database,
    validate_minio,
    validate_chromadb,
    validate_zhipu
)


class TestValidationResult:
    """ValidationResult 测试类"""

    def test_validation_result_success(self):
        """测试成功的验证结果"""
        result = ValidationResult(
            service_name="TestService",
            success=True,
            message="测试成功",
            details={"key": "value"}
        )

        result_dict = result.to_dict()
        assert result_dict["service"] == "TestService"
        assert result_dict["status"] == "success"
        assert result_dict["message"] == "测试成功"
        assert result_dict["details"]["key"] == "value"

    def test_validation_result_failure(self):
        """测试失败的验证结果"""
        result = ValidationResult(
            service_name="TestService",
            success=False,
            message="测试失败"
        )

        result_dict = result.to_dict()
        assert result_dict["service"] == "TestService"
        assert result_dict["status"] == "failed"
        assert result_dict["message"] == "测试失败"
        assert result_dict["details"] == {}


class TestConfigValidator:
    """ConfigValidator 测试类"""

    @pytest.fixture
    def validator(self):
        """创建 ConfigValidator 实例"""
        return ConfigValidator()

    @pytest.mark.asyncio
    async def test_validate_required_env_vars_success(self, validator):
        """测试环境变量验证成功"""
        # Mock settings
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.database_url = "postgresql://user:pass@localhost:5432/test"
            mock_settings.zhipuai_api_key = "valid_api_key_123456"
            mock_settings.minio_access_key = "valid_access_key"
            mock_settings.minio_secret_key = "valid_secret_key_16chars"

            result = await validator.validate_required_env_vars()

            assert result.success == True
            assert "成功" in result.message
            assert result.details["total_required"] == 4

    @pytest.mark.asyncio
    async def test_validate_required_env_vars_missing(self, validator):
        """测试环境变量验证失败（缺少变量）"""
        # Mock settings with missing values
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.database_url = ""
            mock_settings.zhipuai_api_key = "short"
            mock_settings.minio_access_key = "valid_access_key"
            mock_settings.minio_secret_key = "valid_secret_key_16chars"

            result = await validator.validate_required_env_vars()

            assert result.success == False
            assert "缺少变量" in result.message or "无效变量" in result.message
            assert len(result.details["missing"]) > 0 or len(result.details["invalid"]) > 0

    @pytest.mark.asyncio
    async def test_validate_database_connection_success(self, validator):
        """测试数据库连接验证成功"""
        # Mock psycopg2
        with patch('app.core.config_validator.psycopg2') as mock_psycopg2:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = ["PostgreSQL 16.0"]
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

            mock_psycopg2.connect.return_value = mock_connection

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/test"
                mock_settings.database_connect_timeout = 10

                result = await validator.validate_database_connection()

                assert result.success == True
                assert "成功" in result.message
                assert "version" in result.details

    @pytest.mark.asyncio
    async def test_validate_database_connection_failure(self, validator):
        """测试数据库连接验证失败"""
        # Mock psycopg2 to raise exception
        with patch('app.core.config_validator.psycopg2') as mock_psycopg2:
            mock_psycopg2.OperationalError = Exception
            mock_psycopg2.connect.side_effect = Exception("Connection failed")

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/test"
                mock_settings.database_connect_timeout = 10

                result = await validator.validate_database_connection()

                assert result.success == False
                assert "失败" in result.message

    @pytest.mark.asyncio
    async def test_validate_minio_connection_success(self, validator):
        """测试 MinIO 连接验证成功"""
        # Mock MinIO client
        with patch('app.core.config_validator.Minio') as mock_minio:
            mock_client = Mock()
            mock_bucket = Mock()
            mock_bucket.name = "test-bucket"
            mock_client.list_buckets.return_value = [mock_bucket]

            mock_minio.return_value = mock_client

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.minio_endpoint = "localhost:9000"
                mock_settings.minio_access_key = "access_key"
                mock_settings.minio_secret_key = "secret_key"
                mock_settings.minio_secure = False

                result = await validator.validate_minio_connection()

                assert result.success == True
                assert "成功" in result.message
                assert "bucket_count" in result.details

    @pytest.mark.asyncio
    async def test_validate_minio_connection_failure(self, validator):
        """测试 MinIO 连接验证失败"""
        # Mock MinIO client to raise exception
        with patch('app.core.config_validator.Minio') as mock_minio:
            mock_minio.S3Error = Exception
            mock_client = Mock()
            mock_client.list_buckets.side_effect = Exception("MinIO connection failed")
            mock_minio.return_value = mock_client

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.minio_endpoint = "localhost:9000"
                mock_settings.minio_access_key = "access_key"
                mock_settings.minio_secret_key = "secret_key"
                mock_settings.minio_secure = False

                result = await validator.validate_minio_connection()

                assert result.success == False
                assert "失败" in result.message

    @pytest.mark.asyncio
    async def test_validate_chromadb_connection_success(self, validator):
        """测试 ChromaDB 连接验证成功"""
        # Mock ChromaDB client
        with patch('app.core.config_validator.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.name = "test-collection"
            mock_client.list_collections.return_value = [mock_collection]
            mock_client.create_collection.return_value = Mock()
            mock_client.delete_collection.return_value = None

            mock_chromadb.HttpClient.return_value = mock_client

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.chroma_host = "localhost"
                mock_settings.chroma_port = 8000

                result = await validator.validate_chromadb_connection()

                assert result.success == True
                assert "成功" in result.message
                assert "collection_count" in result.details

    @pytest.mark.asyncio
    async def test_validate_chromadb_connection_failure(self, validator):
        """测试 ChromaDB 连接验证失败"""
        # Mock ChromaDB client to raise exception
        with patch('app.core.config_validator.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_client.list_collections.side_effect = Exception("ChromaDB connection failed")
            mock_chromadb.HttpClient.return_value = mock_client

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.chroma_host = "localhost"
                mock_settings.chroma_port = 8000

                result = await validator.validate_chromadb_connection()

                assert result.success == False
                assert "失败" in result.message

    @pytest.mark.asyncio
    async def test_validate_zhipu_api_success(self, validator):
        """测试智谱 API 验证成功"""
        # Mock zhipu_service
        with patch('app.core.config_validator.zhipu_service') as mock_zhipu:
            mock_zhipu.check_connection.return_value = True

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.zhipuai_api_key = "valid_zhipu_api_key"

                result = await validator.validate_zhipu_api()

                assert result.success == True
                assert "成功" in result.message

    @pytest.mark.asyncio
    async def test_validate_zhipu_api_failure(self, validator):
        """测试智谱 API 验证失败"""
        # Mock zhipu_service
        with patch('app.core.config_validator.zhipu_service') as mock_zhipu:
            mock_zhipu.check_connection.return_value = False

            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.zhipuai_api_key = "invalid_zhipu_api_key"

                result = await validator.validate_zhipu_api()

                assert result.success == False
                assert "失败" in result.message

    @pytest.mark.asyncio
    async def test_validate_all_configs_success(self, validator):
        """测试所有配置验证成功"""
        # Mock 所有验证方法
        with patch.object(validator, 'validate_required_env_vars') as mock_env, \
             patch.object(validator, 'validate_database_connection') as mock_db, \
             patch.object(validator, 'validate_minio_connection') as mock_minio, \
             patch.object(validator, 'validate_chromadb_connection') as mock_chroma, \
             patch.object(validator, 'validate_zhipu_api') as mock_zhipu:

            # 设置所有验证结果为成功
            mock_env.return_value = ValidationResult("Environment Variables", True, "成功")
            mock_db.return_value = ValidationResult("PostgreSQL", True, "成功")
            mock_minio.return_value = ValidationResult("MinIO", True, "成功")
            mock_chroma.return_value = ValidationResult("ChromaDB", True, "成功")
            mock_zhipu.return_value = ValidationResult("ZhipuAI", True, "成功")

            result = await validator.validate_all_configs()

            assert result["overall_status"] == "success"
            assert result["total_services"] == 5
            assert result["successful"] == 5
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_validate_all_configs_partial_success(self, validator):
        """测试所有配置验证部分成功"""
        # Mock 验证方法，部分成功
        with patch.object(validator, 'validate_required_env_vars') as mock_env, \
             patch.object(validator, 'validate_database_connection') as mock_db, \
             patch.object(validator, 'validate_minio_connection') as mock_minio, \
             patch.object(validator, 'validate_chromadb_connection') as mock_chroma, \
             patch.object(validator, 'validate_zhipu_api') as mock_zhipu:

            # 设置部分验证结果为成功
            mock_env.return_value = ValidationResult("Environment Variables", True, "成功")
            mock_db.return_value = ValidationResult("PostgreSQL", True, "成功")
            mock_minio.return_value = ValidationResult("MinIO", False, "失败")
            mock_chroma.return_value = ValidationResult("ChromaDB", True, "成功")
            mock_zhipu.return_value = ValidationResult("ZhipuAI", False, "失败")

            result = await validator.validate_all_configs()

            assert result["overall_status"] == "partial_success"
            assert result["total_services"] == 5
            assert result["successful"] == 3
            assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_validate_all_configs_all_failure(self, validator):
        """测试所有配置验证全部失败"""
        # Mock 所有验证方法失败
        with patch.object(validator, 'validate_required_env_vars') as mock_env, \
             patch.object(validator, 'validate_database_connection') as mock_db, \
             patch.object(validator, 'validate_minio_connection') as mock_minio, \
             patch.object(validator, 'validate_chromadb_connection') as mock_chroma, \
             patch.object(validator, 'validate_zhipu_api') as mock_zhipu:

            # 设置所有验证结果为失败
            mock_env.return_value = ValidationResult("Environment Variables", False, "失败")
            mock_db.return_value = ValidationResult("PostgreSQL", False, "失败")
            mock_minio.return_value = ValidationResult("MinIO", False, "失败")
            mock_chroma.return_value = ValidationResult("ChromaDB", False, "失败")
            mock_zhipu.return_value = ValidationResult("ZhipuAI", False, "失败")

            result = await validator.validate_all_configs()

            assert result["overall_status"] == "failed"
            assert result["total_services"] == 5
            assert result["successful"] == 0
            assert result["failed"] == 5


class TestConvenienceFunctions:
    """便捷函数测试类"""

    @pytest.mark.asyncio
    async def test_validate_database_function(self):
        """测试数据库验证便捷函数"""
        with patch('app.core.config_validator.config_validator.validate_database_connection') as mock_validate:
            mock_result = ValidationResult("PostgreSQL", True, "成功")
            mock_validate.return_value = mock_result

            result = await validate_database()

            assert result == mock_result
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_minio_function(self):
        """测试 MinIO 验证便捷函数"""
        with patch('app.core.config_validator.config_validator.validate_minio_connection') as mock_validate:
            mock_result = ValidationResult("MinIO", True, "成功")
            mock_validate.return_value = mock_result

            result = await validate_minio()

            assert result == mock_result
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_chromadb_function(self):
        """测试 ChromaDB 验证便捷函数"""
        with patch('app.core.config_validator.config_validator.validate_chromadb_connection') as mock_validate:
            mock_result = ValidationResult("ChromaDB", True, "成功")
            mock_validate.return_value = mock_result

            result = await validate_chromadb()

            assert result == mock_result
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_zhipu_function(self):
        """测试智谱验证便捷函数"""
        with patch('app.core.config_validator.config_validator.validate_zhipu_api') as mock_validate:
            mock_result = ValidationResult("ZhipuAI", True, "成功")
            mock_validate.return_value = mock_result

            result = await validate_zhipu()

            assert result == mock_result
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_all_function(self):
        """测试全面验证便捷函数"""
        with patch('app.core.config_validator.config_validator.validate_all_configs') as mock_validate:
            mock_result = {
                "overall_status": "success",
                "total_services": 5,
                "successful": 5,
                "failed": 0,
                "results": []
            }
            mock_validate.return_value = mock_result

            result = await validate_all()

            assert result == mock_result
            mock_validate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])