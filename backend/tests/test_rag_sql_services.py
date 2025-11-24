"""
Unit tests for RAG-SQL services
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.database_schema_service import DatabaseSchemaService
from src.services.query_analyzer import QueryAnalyzer
from src.services.sql_generator import SQLGenerator
from src.services.sql_validator import SQLValidator
from src.services.sql_execution_service import SQLExecutionService
from src.services.rag_sql_service import RAGSQLService
from src.models.rag_sql import (
    QueryIntent,
    SQLQuery,
    SQLValidationResult,
    QueryExecutionResult,
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
    QueryType,
)


class TestQueryAnalyzer:
    """Test cases for QueryAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        return QueryAnalyzer()

    @pytest.fixture
    def sample_schema(self):
        """Create sample database schema for testing"""
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
                        ColumnInfo(name="created_at", data_type="TIMESTAMP", is_nullable=True),
                    ]
                ),
                "orders": TableInfo(
                    name="orders",
                    columns=[
                        ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                        ColumnInfo(name="user_id", data_type="INTEGER", is_nullable=False, is_foreign_key=True, foreign_table="users"),
                        ColumnInfo(name="amount", data_type="DECIMAL", is_nullable=False),
                        ColumnInfo(name="order_date", data_type="DATE", is_nullable=False),
                    ]
                )
            },
            discovered_at=datetime.utcnow()
        )

    @pytest.mark.asyncio
    async def test_analyze_simple_select_query(self, analyzer, sample_schema):
        """Test analysis of simple SELECT query"""
        query = "Show me all users"

        intent = await analyzer.analyze_query_intent(query, sample_schema)

        assert intent.original_query == query
        assert intent.query_type == QueryType.SELECT
        assert "users" in intent.target_tables
        assert intent.confidence_score > 0.5

    @pytest.mark.asyncio
    async def test_analyze_aggregate_query(self, analyzer, sample_schema):
        """Test analysis of aggregate query"""
        query = "How many orders do we have?"

        intent = await analyzer.analyze_query_intent(query, sample_schema)

        assert intent.original_query == query
        assert intent.query_type == QueryType.AGGREGATE
        assert "orders" in intent.target_tables
        assert "COUNT" in intent.aggregations

    @pytest.mark.asyncio
    async def test_analyze_join_query(self, analyzer, sample_schema):
        """Test analysis of JOIN query"""
        query = "Show me users and their orders"

        intent = await analyzer.analyze_query_intent(query, sample_schema)

        assert intent.original_query == query
        assert intent.query_type in [QueryType.JOIN, QueryType.SELECT]
        assert "users" in intent.target_tables
        assert "orders" in intent.target_tables

    @pytest.mark.asyncio
    async def test_extract_conditions(self, analyzer):
        """Test condition extraction"""
        query = "Show me users created today with email containing gmail"

        conditions = analyzer._extract_conditions(query)

        assert len(conditions) > 0
        assert any("today" in condition.lower() for condition in conditions)
        assert any("gmail" in condition.lower() for condition in conditions)

    def test_identify_query_type(self, analyzer):
        """Test query type identification"""
        assert analyzer._identify_query_type("show me users") == QueryType.SELECT
        assert analyzer._identify_query_type("how many users") == QueryType.AGGREGATE
        assert analyzer._identify_query_type("users and their orders") == QueryType.JOIN


class TestSQLGenerator:
    """Test cases for SQLGenerator"""

    @pytest.fixture
    def generator(self):
        return SQLGenerator()

    @pytest.fixture
    def sample_intent(self):
        """Create sample query intent for testing"""
        return QueryIntent(
            original_query="Show me all users",
            query_type=QueryType.SELECT,
            target_tables=["users"],
            target_columns=["users.name", "users.email"],
            conditions=[],
            aggregations=[],
            groupings=[],
            orderings=[],
            confidence_score=0.9
        )

    @pytest.fixture
    def sample_schema(self):
        """Create sample database schema for testing"""
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

    @pytest.mark.asyncio
    async def test_generate_select_sql(self, generator, sample_intent, sample_schema):
        """Test SELECT SQL generation"""
        sql_query = await generator.generate_sql(sample_intent, sample_schema)

        assert sql_query.query.upper().startswith("SELECT")
        assert "FROM users" in sql_query.query.upper()
        assert "name" in sql_query.query and "email" in sql_query.query
        assert sql_query.query_type == QueryType.SELECT

    @pytest.mark.asyncio
    async def test_generate_aggregate_sql(self, generator, sample_schema):
        """Test aggregate SQL generation"""
        intent = QueryIntent(
            original_query="How many users",
            query_type=QueryType.AGGREGATE,
            target_tables=["users"],
            target_columns=[],
            conditions=[],
            aggregations=["COUNT"],
            groupings=[],
            orderings=[],
            confidence_score=0.9
        )

        sql_query = await generator.generate_sql(intent, sample_schema)

        assert "COUNT(" in sql_query.query.upper()
        assert sql_query.query_type == QueryType.AGGREGATE

    @pytest.mark.asyncio
    async def test_generate_join_sql(self, generator, sample_schema):
        """Test JOIN SQL generation"""
        # Add orders table to schema
        sample_schema.tables["orders"] = TableInfo(
            name="orders",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                ColumnInfo(name="user_id", data_type="INTEGER", is_nullable=False, is_foreign_key=True, foreign_table="users"),
            ]
        )

        intent = QueryIntent(
            original_query="Users and their orders",
            query_type=QueryType.JOIN,
            target_tables=["users", "orders"],
            target_columns=["users.name", "orders.id"],
            conditions=[],
            aggregations=[],
            groupings=[],
            orderings=[],
            confidence_score=0.8
        )

        sql_query = await generator.generate_sql(intent, sample_schema)

        assert "JOIN" in sql_query.query.upper()
        assert "users" in sql_query.query and "orders" in sql_query.query


class TestSQLValidator:
    """Test cases for SQLValidator"""

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    @pytest.fixture
    def sample_schema(self):
        """Create sample database schema for testing"""
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
                    ]
                )
            }
        )

    @pytest.mark.asyncio
    async def test_validate_safe_select(self, validator, sample_schema):
        """Test validation of safe SELECT query"""
        sql_query = SQLQuery(query="SELECT id, name FROM users")

        result = await validator.validate_sql(sql_query, sample_schema, "test_tenant")

        assert result.is_valid == True
        assert len(result.validation_errors) == 0
        assert result.risk_level == "LOW"

    @pytest.mark.asyncio
    async def test_validate_dangerous_query(self, validator, sample_schema):
        """Test validation of dangerous query"""
        sql_query = SQLQuery(query="DROP TABLE users")

        result = await validator.validate_sql(sql_query, sample_schema, "test_tenant")

        assert result.is_valid == False
        assert len(result.validation_errors) > 0
        assert any("DROP" in error for error in result.validation_errors)

    @pytest.mark.asyncio
    async def test_validate_sql_injection_attempt(self, validator, sample_schema):
        """Test validation of SQL injection attempt"""
        sql_query = SQLQuery(query="SELECT * FROM users WHERE id = 1; DROP TABLE users; --")

        result = await validator.validate_sql(sql_query, sample_schema, "test_tenant")

        assert result.is_valid == False
        assert len(result.validation_errors) > 0
        assert any("injection" in warning.lower() for warning in result.security_warnings)

    @pytest.mark.asyncio
    async def test_validate_invalid_table_reference(self, validator, sample_schema):
        """Test validation of query with invalid table reference"""
        sql_query = SQLQuery(query="SELECT * FROM invalid_table")

        result = await validator.validate_sql(sql_query, sample_schema, "test_tenant")

        assert result.is_valid == False
        assert any("invalid_table" in error for error in result.validation_errors)


class TestSQLExecutionService:
    """Test cases for SQLExecutionService"""

    @pytest.fixture
    def executor(self):
        return SQLExecutionService()

    @pytest.mark.asyncio
    async def test_decrypt_connection_string(self, executor):
        """Test connection string decryption"""
        # This test requires actual encryption key setup
        # For now, just test that the method exists and handles errors
        with pytest.raises(ValueError):
            executor._decrypt_connection_string("invalid_encrypted_string")

    @pytest.mark.asyncio
    async def test_estimate_query_cost(self, executor):
        """Test query cost estimation"""
        simple_query = "SELECT * FROM users"
        complex_query = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id WHERE u.created_at > '2023-01-01' GROUP BY u.name"

        simple_cost = executor._estimate_query_cost(simple_query)
        complex_cost = executor._estimate_query_cost(complex_query)

        assert complex_cost > simple_cost

    def test_process_value(self, executor):
        """Test value processing for JSON serialization"""
        test_datetime = datetime.utcnow()
        test_dict = {"key": "value"}

        processed_datetime = executor._process_value(test_datetime)
        processed_dict = executor._process_value(test_dict)
        processed_none = executor._process_value(None)

        assert isinstance(processed_datetime, str)
        assert isinstance(processed_dict, str)
        assert processed_none is None


class TestDatabaseSchemaService:
    """Test cases for DatabaseSchemaService"""

    @pytest.fixture
    def schema_service(self):
        return DatabaseSchemaService()

    def test_normalize_data_type(self, schema_service):
        """Test data type normalization"""
        # Test various PostgreSQL data types
        assert schema_service._normalize_data_type({
            'data_type': 'character varying',
            'character_maximum_length': 50
        }) == "VARCHAR(50)"

        assert schema_service._normalize_data_type({
            'data_type': 'numeric',
            'numeric_precision': 10,
            'numeric_scale': 2
        }) == "NUMERIC(10,2)"

        assert schema_service._normalize_data_type({
            'data_type': 'timestamp without time zone'
        }) == "TIMESTAMP"

    def test_find_join_condition(self, schema_service):
        """Test join condition finding"""
        # Create table info with foreign key relationship
        users_table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
            ]
        )

        orders_table = TableInfo(
            name="orders",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnInfo(name="user_id", data_type="INTEGER", is_foreign_key=True, foreign_table="users", foreign_column="id"),
            ]
        )

        # Test finding join condition
        join_condition = schema_service._find_join_condition(orders_table, users_table)

        assert join_condition == "orders.user_id = users.id"

    @pytest.mark.asyncio
    async def test_cache_operations(self, schema_service):
        """Test schema cache operations"""
        # Test cache miss
        cached_schema = await schema_service.get_cached_schema("test_tenant", 1)
        assert cached_schema is None

        # Test cache invalidation
        await schema_service.invalidate_schema_cache("test_tenant", 1)
        # Should not raise any errors


class TestRAGSQLService:
    """Test cases for RAGSQLService integration"""

    @pytest.fixture
    def rag_sql_service(self):
        return RAGSQLService()

    def test_generate_cache_key(self, rag_sql_service):
        """Test cache key generation"""
        key1 = rag_sql_service._generate_cache_key("test query", "tenant1", 1)
        key2 = rag_sql_service._generate_cache_key("test query", "tenant1", 1)
        key3 = rag_sql_service._generate_cache_key("different query", "tenant1", 1)

        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys

    def test_cache_key_length(self, rag_sql_service):
        """Test that cache keys have consistent length"""
        key = rag_sql_service._generate_cache_key("test query", "tenant1", 1)
        assert len(key) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_simplify_query(self, rag_sql_service):
        """Test query simplification"""
        complex_query = SQLQuery(
            query="SELECT u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id WHERE u.active = true GROUP BY u.name ORDER BY order_count DESC LIMIT 10",
            query_type=QueryType.JOIN
        )

        simple_intent = QueryIntent(
            original_query="show users",
            query_type=QueryType.SELECT,
            target_tables=["users"],
            target_columns=[],
            conditions=[],
            aggregations=[],
            groupings=[],
            orderings=[],
            confidence_score=0.8
        )

        simplified = await rag_sql_service._simplify_query(complex_query, simple_intent)

        assert "JOIN" not in simplified.query.upper()
        assert simplified.query_type == QueryType.SELECT

    @pytest.mark.asyncio
    async def test_health_status(self, rag_sql_service):
        """Test health status reporting"""
        health = await rag_sql_service.get_health_status()

        assert "cache_size" in health
        assert "service_status" in health
        assert "last_updated" in health
        assert health["service_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_cleanup(self, rag_sql_service):
        """Test service cleanup"""
        # Add some data to caches
        rag_sql_service.query_cache["test"] = "value"
        rag_sql_service.schema_cache["test"] = "value"
        rag_sql_service.stats_cache["test"] = "value"

        # Verify data exists
        assert len(rag_sql_service.query_cache) > 0
        assert len(rag_sql_service.schema_cache) > 0
        assert len(rag_sql_service.stats_cache) > 0

        # Cleanup
        await rag_sql_service.cleanup()

        # Verify caches are cleared
        assert len(rag_sql_service.query_cache) == 0
        assert len(rag_sql_service.schema_cache) == 0
        assert len(rag_sql_service.stats_cache) == 0


class TestIntegration:
    """Integration tests for RAG-SQL services"""

    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self):
        """Test end-to-end query processing flow"""
        # Create test instances
        analyzer = QueryAnalyzer()
        generator = SQLGenerator()
        validator = SQLValidator()

        # Create test schema
        schema = DatabaseSchema(
            tenant_id="test_tenant",
            connection_id=1,
            database_name="test_db",
            tables={
                "users": TableInfo(
                    name="users",
                    columns=[
                        ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
                        ColumnInfo(name="name", data_type="VARCHAR", is_nullable=False),
                    ]
                )
            }
        )

        # Test query processing flow
        query = "Show me all users"

        # Step 1: Analyze query
        intent = await analyzer.analyze_query_intent(query, schema)
        assert intent.query_type == QueryType.SELECT

        # Step 2: Generate SQL
        sql_query = await generator.generate_sql(intent, schema)
        assert "SELECT" in sql_query.query.upper()

        # Step 3: Validate SQL
        validation_result = await validator.validate_sql(sql_query, schema, "test_tenant")
        assert validation_result.is_valid == True

        # Step 4: Mock execution (since we don't have real database)
        mock_execution_result = QueryExecutionResult(
            execution_time_ms=50,
            row_count=0,
            columns=[
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"}
            ],
            data=[],
            has_more=False
        )

        # Verify the flow works end-to-end
        assert intent.original_query == query
        assert sql_query.query_type == QueryType.SELECT
        assert validation_result.risk_level == "LOW"


if __name__ == "__main__":
    pytest.main([__file__])