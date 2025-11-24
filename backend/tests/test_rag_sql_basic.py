"""
Basic RAG-SQL functionality tests (without external dependencies)
"""

import pytest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.rag_sql import (
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
    QueryIntent,
    SQLQuery,
    SQLValidationResult,
    QueryExecutionResult,
    RAGSQLResult,
    QueryType,
)


class TestRAGSQLModels:
    """Test RAG-SQL data models"""

    def test_column_info_creation(self):
        """Test ColumnInfo model creation"""
        column = ColumnInfo(
            name="id",
            data_type="INTEGER",
            is_nullable=False,
            is_primary_key=True
        )

        assert column.name == "id"
        assert column.data_type == "INTEGER"
        assert column.is_nullable == False
        assert column.is_primary_key == True
        assert column.is_foreign_key == False

    def test_table_info_creation(self):
        """Test TableInfo model creation"""
        columns = [
            ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
            ColumnInfo(name="name", data_type="VARCHAR", is_nullable=False)
        ]

        table = TableInfo(
            name="users",
            columns=columns,
            row_count=100,
            sample_data=[{"id": 1, "name": "John"}]
        )

        assert table.name == "users"
        assert len(table.columns) == 2
        assert table.row_count == 100
        assert len(table.sample_data) == 1

    def test_database_schema_creation(self):
        """Test DatabaseSchema model creation"""
        table_info = TableInfo(
            name="users",
            columns=[ColumnInfo(name="id", data_type="INTEGER", is_nullable=False)]
        )

        schema = DatabaseSchema(
            tenant_id="test_tenant",
            connection_id=1,
            database_name="test_db",
            tables={"users": table_info}
        )

        assert schema.tenant_id == "test_tenant"
        assert schema.connection_id == 1
        assert schema.database_name == "test_db"
        assert "users" in schema.tables

    def test_query_intent_creation(self):
        """Test QueryIntent model creation"""
        intent = QueryIntent(
            original_query="Show me all users",
            query_type=QueryType.SELECT,
            target_tables=["users"],
            target_columns=["users.name", "users.email"],
            confidence_score=0.9
        )

        assert intent.original_query == "Show me all users"
        assert intent.query_type == QueryType.SELECT
        assert "users" in intent.target_tables
        assert intent.confidence_score == 0.9

    def test_sql_query_creation(self):
        """Test SQLQuery model creation"""
        sql_query = SQLQuery(
            query="SELECT id, name FROM users",
            query_type=QueryType.SELECT,
            estimated_cost=10.5
        )

        assert sql_query.query == "SELECT id, name FROM users"
        assert sql_query.query_type == QueryType.SELECT
        assert sql_query.estimated_cost == 10.5
        assert sql_query.parameters == []

    def test_sql_validation_result_creation(self):
        """Test SQLValidationResult model creation"""
        validation = SQLValidationResult(
            is_valid=True,
            validation_errors=[],
            security_warnings=["Consider adding LIMIT clause"],
            risk_level="LOW",
            suggestions=["Use specific columns instead of *"]
        )

        assert validation.is_valid == True
        assert len(validation.validation_errors) == 0
        assert len(validation.security_warnings) == 1
        assert validation.risk_level == "LOW"

    def test_query_execution_result_creation(self):
        """Test QueryExecutionResult model creation"""
        execution = QueryExecutionResult(
            execution_time_ms=150,
            row_count=5,
            columns=[
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"}
            ],
            data=[
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ],
            has_more=False
        )

        assert execution.execution_time_ms == 150
        assert execution.row_count == 5
        assert len(execution.columns) == 2
        assert len(execution.data) == 2
        assert execution.has_more == False

    def test_rag_sql_result_creation(self):
        """Test RAGSQLResult model creation"""
        validation = SQLValidationResult(is_valid=True, validation_errors=[], security_warnings=[], risk_level="LOW")
        execution = QueryExecutionResult(
            execution_time_ms=200,
            row_count=3,
            columns=[{"name": "id", "type": "integer"}],
            data=[{"id": 1}, {"id": 2}, {"id": 3}],
            has_more=False
        )

        result = RAGSQLResult(
            tenant_id="test_tenant",
            original_query="Show users",
            generated_sql="SELECT * FROM users",
            validation_result=validation,
            execution_result=execution,
            processing_time_ms=500,
            correction_attempts=0,
            explanation="Query processed successfully",
            confidence_score=0.85,
            processing_steps=["Analyze", "Generate", "Execute"]
        )

        assert result.tenant_id == "test_tenant"
        assert result.original_query == "Show users"
        assert result.generated_sql == "SELECT * FROM users"
        assert result.processing_time_ms == 500
        assert result.confidence_score == 0.85
        assert len(result.processing_steps) == 3


class TestQueryAnalyzerBasic:
    """Test basic query analyzer functionality (without imports)"""

    def test_query_type_patterns(self):
        """Test query type pattern matching"""
        # Test SELECT patterns
        select_patterns = [
            r'\b(show|get|list|display|find|search|look up|retrieve|fetch|what|which|who|where|when)\b'
        ]

        test_queries = [
            ("show me users", True),
            ("get all orders", True),
            ("list products", True),
            ("update user profile", False),
            ("delete old records", False)
        ]

        import re
        for query, should_match in test_queries:
            matches = any(re.search(pattern, query, re.IGNORECASE) for pattern in select_patterns)
            assert matches == should_match, f"Query '{query}' matching failed"

    def test_aggregation_patterns(self):
        """Test aggregation pattern matching"""
        aggregation_patterns = [
            r'\b(sum|total|count|average|avg|mean|max|min|total sum|overall)\b'
        ]

        test_queries = [
            ("sum of all sales", True),
            ("count the users", True),
            ("average order value", True),
            ("list all products", False),
            ("show user details", False)
        ]

        import re
        for query, should_match in test_queries:
            matches = any(re.search(pattern, query, re.IGNORECASE) for pattern in aggregation_patterns)
            assert matches == should_match, f"Query '{query}' aggregation matching failed"

    def test_time_pattern_extraction(self):
        """Test time pattern extraction"""
        time_patterns = [
            r'\b(today|yesterday|tomorrow|now|current)\b',
            r'\b(this week|last week|next week)\b',
            r'\b(this month|last month|next month)\b'
        ]

        test_queries = [
            ("orders from today", True),
            ("sales last week", True),
            ("users created this month", True),
            ("all products", False),
            ("customer information", False)
        ]

        import re
        for query, should_match in test_queries:
            matches = any(re.search(pattern, query, re.IGNORECASE) for pattern in time_patterns)
            assert matches == should_match, f"Query '{query}' time pattern matching failed"


class TestSQLGeneratorBasic:
    """Test basic SQL generator functionality"""

    def test_sql_template_formatting(self):
        """Test SQL template formatting"""
        templates = {
            "select": "SELECT {columns} FROM {table}{where}{order}{limit}",
            "aggregate": "SELECT {aggregations} FROM {table}{where}{group_by}{having}{order}{limit}"
        }

        # Test SELECT template
        select_sql = templates["select"].format(
            columns="id, name",
            table="users",
            where=" WHERE active = true",
            order=" ORDER BY name",
            limit=" LIMIT 10"
        )

        expected = "SELECT id, name FROM users WHERE active = true ORDER BY name LIMIT 10"
        assert select_sql == expected

        # Test template without optional parts
        simple_select = templates["select"].format(
            columns="*",
            table="users",
            where="",
            order="",
            limit=""
        )

        assert simple_select == "SELECT * FROM users"

    def test_column_name_normalization(self):
        """Test column name normalization"""
        # Test table prefix addition
        columns = ["id", "name", "email"]
        table_name = "users"

        normalized_columns = [f"{table_name}.{col}" for col in columns]
        expected = ["users.id", "users.name", "users.email"]

        assert normalized_columns == expected

    def test_where_clause_building(self):
        """Test WHERE clause building"""
        conditions = ["active = true", "created_at > '2023-01-01'"]

        where_clause = " WHERE " + " AND ".join(conditions)
        expected = " WHERE active = true AND created_at > '2023-01-01'"

        assert where_clause == expected


class TestSQLValidatorBasic:
    """Test basic SQL validator functionality"""

    def test_dangerous_keyword_detection(self):
        """Test dangerous keyword detection"""
        dangerous_keywords = {
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXECUTE', 'EXEC', 'GRANT', 'REVOKE', 'UNION'
        }

        safe_queries = [
            "SELECT id, name FROM users",
            "SELECT COUNT(*) FROM orders WHERE status = 'active'",
            "SELECT * FROM products ORDER BY name LIMIT 10"
        ]

        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM orders WHERE id = 1",
            "UPDATE users SET name = 'John' WHERE id = 1",
            "INSERT INTO users (name) VALUES ('Test')",
            "SELECT * FROM users UNION SELECT * FROM admins"
        ]

        import re
        for query in safe_queries:
            query_upper = query.upper()
            found_dangerous = any(
                re.search(r'\b' + keyword + r'\b', query_upper)
                for keyword in dangerous_keywords
            )
            assert not found_dangerous, f"Safe query flagged as dangerous: {query}"

        for query in dangerous_queries:
            query_upper = query.upper()
            found_dangerous = any(
                re.search(r'\b' + keyword + r'\b', query_upper)
                for keyword in dangerous_keywords
            )
            assert found_dangerous, f"Dangerous query not detected: {query}"

    def test_sql_injection_pattern_detection(self):
        """Test SQL injection pattern detection"""
        injection_patterns = [
            r"(--|#|/\*|\*/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\'\s*;\s*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b)",
            r"(\bUNION\b\s+\bSELECT\b)"
        ]

        injection_attempts = [
            "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
            "SELECT * FROM users WHERE name = 'test' OR 1=1",
            "SELECT * FROM users WHERE id = 1' UNION SELECT * FROM passwords --",
            "SELECT * FROM users /* comment */ WHERE active = true"
        ]

        import re
        for query in injection_attempts:
            found_injection = any(
                re.search(pattern, query, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                for pattern in injection_patterns
            )
            assert found_injection, f"SQL injection not detected: {query}"


class TestIntegrationBasic:
    """Basic integration tests without external dependencies"""

    def test_end_to_end_model_flow(self):
        """Test end-to-end model creation flow"""
        # Create column info
        columns = [
            ColumnInfo(name="id", data_type="INTEGER", is_nullable=False, is_primary_key=True),
            ColumnInfo(name="name", data_type="VARCHAR", is_nullable=False)
        ]

        # Create table info
        table = TableInfo(
            name="users",
            columns=columns,
            row_count=100
        )

        # Create schema
        schema = DatabaseSchema(
            tenant_id="test_tenant",
            connection_id=1,
            database_name="test_db",
            tables={"users": table}
        )

        # Create query intent
        intent = QueryIntent(
            original_query="Show me all users",
            query_type=QueryType.SELECT,
            target_tables=["users"],
            target_columns=["users.id", "users.name"],
            confidence_score=0.9
        )

        # Create SQL query
        sql_query = SQLQuery(
            query="SELECT id, name FROM users",
            query_type=QueryType.SELECT
        )

        # Create validation result
        validation = SQLValidationResult(
            is_valid=True,
            validation_errors=[],
            security_warnings=[],
            risk_level="LOW"
        )

        # Create execution result
        execution = QueryExecutionResult(
            execution_time_ms=100,
            row_count=5,
            columns=[
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"}
            ],
            data=[
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ],
            has_more=False
        )

        # Create final result
        result = RAGSQLResult(
            tenant_id=schema.tenant_id,
            original_query=intent.original_query,
            generated_sql=sql_query.query,
            validation_result=validation,
            execution_result=execution,
            processing_time_ms=200,
            correction_attempts=0,
            explanation="Query processed successfully",
            confidence_score=intent.confidence_score,
            processing_steps=["Analyze", "Generate", "Validate", "Execute"]
        )

        # Verify the complete flow
        assert result.tenant_id == "test_tenant"
        assert result.original_query == "Show me all users"
        assert result.generated_sql == "SELECT id, name FROM users"
        assert result.validation_result.is_valid == True
        assert result.execution_result.row_count == 5
        assert result.confidence_score == 0.9
        assert len(result.processing_steps) == 4

    def test_error_handling_flow(self):
        """Test error handling in model creation"""
        # Test validation error case
        validation_error = SQLValidationResult(
            is_valid=False,
            validation_errors=["Table 'invalid_table' does not exist"],
            security_warnings=[],
            risk_level="HIGH"
        )

        # Test execution error case
        execution_error = QueryExecutionResult(
            execution_time_ms=50,
            row_count=0,
            columns=[],
            data=[],
            has_more=False
        )

        # Create error result
        error_result = RAGSQLResult(
            tenant_id="test_tenant",
            original_query="Invalid query",
            generated_sql="SELECT * FROM invalid_table",
            validation_result=validation_error,
            execution_result=execution_error,
            processing_time_ms=100,
            correction_attempts=0,
            explanation="Error: Table 'invalid_table' does not exist",
            confidence_score=0.0,
            processing_steps=["Analyze", "Generate", "Validate", "Error"]
        )

        # Verify error handling
        assert error_result.validation_result.is_valid == False
        assert len(error_result.validation_result.validation_errors) > 0
        assert error_result.execution_result.row_count == 0
        assert error_result.confidence_score == 0.0
        assert "Error:" in error_result.explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])