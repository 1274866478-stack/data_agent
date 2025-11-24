"""
Unit tests for RAG-SQL API endpoints
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.endpoints.rag_sql import router
from src.models.rag_sql import (
    RAGSQLResult,
    DatabaseSchema,
    SQLValidationResult,
    QueryExecutionResult,
    QueryType,
)


class TestRAGSQLEndpoints:
    """Test cases for RAG-SQL API endpoints"""

    @pytest.fixture
    def app(self):
        """Create FastAPI test app"""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rag-sql")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_rag_sql_result(self):
        """Create mock RAG-SQL result"""
        return RAGSQLResult(
            tenant_id="test_tenant",
            original_query="Show me all users",
            generated_sql="SELECT id, name FROM users",
            validation_result=SQLValidationResult(
                is_valid=True,
                validation_errors=[],
                security_warnings=[],
                risk_level="LOW",
                suggestions=[]
            ),
            execution_result=QueryExecutionResult(
                execution_time_ms=100,
                row_count=5,
                columns=[
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"}
                ],
                data=[
                    {"id": 1, "name": "John"},
                    {"id": 2, "name": "Jane"},
                    {"id": 3, "name": "Bob"},
                    {"id": 4, "name": "Alice"},
                    {"id": 5, "name": "Charlie"}
                ],
                has_more=False
            ),
            processing_time_ms=250,
            correction_attempts=0,
            explanation="Query processed successfully",
            confidence_score=0.9,
            processing_steps=["Analyzed query", "Generated SQL", "Executed query"]
        )

    @pytest.fixture
    def mock_database_schema(self):
        """Create mock database schema"""
        from src.models.rag_sql import TableInfo, ColumnInfo
        return DatabaseSchema(
            tenant_id="test_tenant",
            connection_id=1,
            database_name="test_db",
            tables={
                "users": TableInfo(
                    name="users",
                    columns=[
                        ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                        ColumnInfo(name="name", data_type="VARCHAR", is_nullable=False),
                        ColumnInfo(name="email", data_type="VARCHAR", is_nullable=False),
                    ]
                )
            }
        )

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_process_natural_language_query_success(
        self,
        mock_service,
        mock_get_conn_string,
        mock_get_tenant,
        client,
        mock_rag_sql_result
    ):
        """Test successful natural language query processing"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"
        mock_service.process_natural_language_query = AsyncMock(return_value=mock_rag_sql_result)

        # Make request
        response = client.post(
            "/api/v1/rag-sql/query",
            json={
                "query": "Show me all users",
                "connection_id": 1,
                "force_refresh": False,
                "enable_cache": True
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["original_query"] == "Show me all users"
        assert data["generated_sql"] == "SELECT id, name FROM users"
        assert data["validation_result"]["is_valid"] == True
        assert data["execution_result"]["row_count"] == 5
        assert data["confidence_score"] == 0.9

        # Verify mocks were called
        mock_service.process_natural_language_query.assert_called_once()

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    def test_process_natural_language_query_missing_connection(
        self,
        mock_get_conn_string,
        mock_get_tenant,
        client
    ):
        """Test query processing with missing connection"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = None

        # Make request
        response = client.post(
            "/api/v1/rag-sql/query",
            json={
                "query": "Show me all users",
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.schema_service')
    def test_discover_database_schema_success(
        self,
        mock_schema_service,
        mock_get_conn_string,
        mock_get_tenant,
        client,
        mock_database_schema
    ):
        """Test successful database schema discovery"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"
        mock_schema_service.discover_tenant_schema = AsyncMock(return_value=mock_database_schema)

        # Make request
        response = client.post(
            "/api/v1/rag-sql/schema/discover",
            json={
                "connection_id": 1,
                "force_refresh": False
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test_tenant"
        assert data["database_name"] == "test_db"
        assert "users" in data["tables"]
        assert len(data["tables"]["users"]["columns"]) == 3

        # Verify mocks were called
        mock_schema_service.discover_tenant_schema.assert_called_once()

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.schema_service')
    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_validate_sql_query_success(
        self,
        mock_rag_service,
        mock_schema_service,
        mock_get_conn_string,
        mock_get_tenant,
        client,
        mock_database_schema
    ):
        """Test successful SQL query validation"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"
        mock_schema_service.discover_tenant_schema = AsyncMock(return_value=mock_database_schema)

        mock_validation_result = SQLValidationResult(
            is_valid=True,
            validation_errors=[],
            security_warnings=[],
            risk_level="LOW",
            suggestions=[]
        )
        mock_rag_service.sql_validator.validate_sql = AsyncMock(return_value=mock_validation_result)

        # Make request
        response = client.post(
            "/api/v1/rag-sql/sql/validate",
            json={
                "query": "SELECT id, name FROM users",
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == True
        assert data["risk_level"] == "LOW"
        assert len(data["validation_errors"]) == 0

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.sql_executor')
    def test_test_database_connection_success(
        self,
        mock_sql_executor,
        mock_get_conn_string,
        mock_get_tenant,
        client
    ):
        """Test successful database connection test"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"

        mock_test_result = {
            "success": True,
            "connection_time_ms": 50,
            "database_name": "test_db",
            "version": "PostgreSQL 14.0",
            "message": "Connection successful"
        }
        mock_sql_executor.test_connection = AsyncMock(return_value=mock_test_result)

        # Make request
        response = client.post(
            "/api/v1/rag-sql/connection/test",
            json={
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["database_name"] == "test_db"
        assert data["connection_time_ms"] == 50

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_get_rag_sql_stats_success(
        self,
        mock_rag_service,
        mock_get_tenant,
        client
    ):
        """Test successful stats retrieval"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"

        from src.models.rag_sql import RAGSQLStats
        mock_stats = RAGSQLStats(
            tenant_id="test_tenant",
            total_queries=100,
            successful_queries=95,
            failed_queries=5,
            average_processing_time_ms=250.5,
            average_execution_time_ms=120.3,
            most_queried_tables=["users", "orders"],
            query_types={"SELECT": 60, "AGGREGATE": 40}
        )
        mock_rag_service.get_stats = AsyncMock(return_value=mock_stats)

        # Make request
        response = client.get(
            "/api/v1/rag-sql/stats/test_tenant",
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test_tenant"
        assert data["total_queries"] == 100
        assert data["successful_queries"] == 95
        assert data["average_processing_time_ms"] == 250.5

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    def test_get_rag_sql_stats_access_denied(
        self,
        mock_get_tenant,
        client
    ):
        """Test stats retrieval access denied"""
        # Setup mocks - tenant trying to access different tenant's stats
        mock_get_tenant.return_value = "different_tenant"

        # Make request
        response = client.get(
            "/api/v1/rag-sql/stats/test_tenant",
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_clear_tenant_cache_success(
        self,
        mock_rag_service,
        mock_get_tenant,
        client
    ):
        """Test successful tenant cache clearing"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_rag_service.clear_cache = AsyncMock()

        # Make request
        response = client.delete(
            "/api/v1/rag-sql/cache/test_tenant",
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "cache cleared" in data["message"].lower()
        mock_rag_service.clear_cache.assert_called_once_with(tenant_id="test_tenant")

    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_get_rag_sql_health_success(
        self,
        mock_rag_service,
        client
    ):
        """Test successful health status retrieval"""
        # Setup mocks
        mock_health_status = {
            "cache_size": 10,
            "schema_cache_size": 5,
            "stats_cache_size": 3,
            "active_tenants": 8,
            "service_status": "healthy",
            "last_updated": "2023-12-01T12:00:00"
        }
        mock_rag_service.get_health_status = AsyncMock(return_value=mock_health_status)

        # Make request
        response = client.get("/api/v1/rag-sql/health")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["service_status"] == "healthy"
        assert data["cache_size"] == 10
        assert data["active_tenants"] == 8

    def test_natural_language_query_request_validation(self, client):
        """Test request validation for natural language query endpoint"""
        # Test missing required fields
        response = client.post(
            "/api/v1/rag-sql/query",
            json={},
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 422

        # Test invalid query length
        response = client.post(
            "/api/v1/rag-sql/query",
            json={
                "query": "a" * 1001,  # Too long
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 422

    def test_sql_validation_request_validation(self, client):
        """Test request validation for SQL validation endpoint"""
        # Test missing required fields
        response = client.post(
            "/api/v1/rag-sql/sql/validate",
            json={},
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 422

        # Test empty query
        response = client.post(
            "/api/v1/rag-sql/sql/validate",
            json={
                "query": "",
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 422


class TestAPIErrorHandling:
    """Test cases for API error handling"""

    @pytest.fixture
    def app(self):
        """Create FastAPI test app"""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/rag-sql")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.rag_sql_service')
    def test_query_processing_value_error(
        self,
        mock_service,
        mock_get_conn_string,
        mock_get_tenant,
        client
    ):
        """Test handling of ValueError during query processing"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"
        mock_service.process_natural_language_query = AsyncMock(
            side_effect=ValueError("Query analysis confidence too low: 0.1")
        )

        # Make request
        response = client.post(
            "/api/v1/rag-sql/query",
            json={
                "query": "Invalid query",
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 400
        assert "confidence too low" in response.json()["detail"].lower()

    @patch('src.api.v1.endpoints.rag_sql.get_current_tenant')
    @patch('src.api.v1.endpoints.rag_sql._get_connection_string')
    @patch('src.api.v1.endpoints.rag_sql.schema_service')
    def test_schema_discovery_exception(
        self,
        mock_schema_service,
        mock_get_conn_string,
        mock_get_tenant,
        client
    ):
        """Test handling of exceptions during schema discovery"""
        # Setup mocks
        mock_get_tenant.return_value = "test_tenant"
        mock_get_conn_string.return_value = "encrypted_connection_string"
        mock_schema_service.discover_tenant_schema = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Make request
        response = client.post(
            "/api/v1/rag-sql/schema/discover",
            json={
                "connection_id": 1
            },
            headers={"Authorization": "Bearer test_token"}
        )

        # Assertions
        assert response.status_code == 500
        assert "failed to discover" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__])