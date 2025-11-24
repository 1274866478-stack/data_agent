"""
RAG-SQL related data models for Data Agent V4 Backend
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class QueryType(str, Enum):
    """Query type enumeration"""
    SELECT = "SELECT"
    AGGREGATE = "AGGREGATE"
    JOIN = "JOIN"
    FILTER = "FILTER"
    SORT = "SORT"


class ColumnInfo(BaseModel):
    """Column information model"""
    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="PostgreSQL data type")
    is_nullable: bool = Field(..., description="Whether column allows NULL values")
    default_value: Optional[str] = Field(None, description="Default value")
    is_primary_key: bool = Field(False, description="Whether column is primary key")
    is_foreign_key: bool = Field(False, description="Whether column is foreign key")
    foreign_table: Optional[str] = Field(None, description="Foreign table reference")
    foreign_column: Optional[str] = Field(None, description="Foreign column reference")


class TableInfo(BaseModel):
    """Table information model"""
    name: str = Field(..., description="Table name")
    columns: List[ColumnInfo] = Field(..., description="List of columns")
    row_count: Optional[int] = Field(None, description="Estimated row count")
    sample_data: List[Dict[str, Any]] = Field(default_factory=list, description="Sample data rows")
    relationships: List[Dict[str, str]] = Field(default_factory=list, description="Table relationships")


class DatabaseSchema(BaseModel):
    """Database schema model"""
    tenant_id: str = Field(..., description="Tenant ID")
    connection_id: int = Field(..., description="Data source connection ID")
    database_name: str = Field(..., description="Database name")
    tables: Dict[str, TableInfo] = Field(default_factory=dict, description="Table information")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp")
    version: str = Field(default="1.0", description="Schema version")

    class Config:
        from_attributes = True


class QueryIntent(BaseModel):
    """Query intent analysis result"""
    original_query: str = Field(..., description="Original natural language query")
    query_type: QueryType = Field(..., description="Identified query type")
    target_tables: List[str] = Field(..., description="Target tables for the query")
    target_columns: List[str] = Field(..., description="Target columns for the query")
    conditions: List[str] = Field(default_factory=list, description="Extracted conditions")
    aggregations: List[str] = Field(default_factory=list, description="Aggregation functions")
    groupings: List[str] = Field(default_factory=list, description="Group by columns")
    orderings: List[str] = Field(default_factory=list, description="Order by columns")
    confidence_score: float = Field(..., description="Confidence score (0-1)")

    class Config:
        from_attributes = True


class SQLQuery(BaseModel):
    """SQL query model"""
    query: str = Field(..., description="Generated SQL query")
    parameters: List[Any] = Field(default_factory=list, description="Query parameters")
    query_type: QueryType = Field(..., description="Query type")
    estimated_cost: Optional[float] = Field(None, description="Query execution cost")
    execution_plan: Optional[Dict[str, Any]] = Field(None, description="Query execution plan")

    class Config:
        from_attributes = True


class SQLValidationResult(BaseModel):
    """SQL validation result"""
    is_valid: bool = Field(..., description="Whether SQL is valid")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    security_warnings: List[str] = Field(default_factory=list, description="Security warnings")
    risk_level: str = Field(default="LOW", description="Risk level (LOW/MEDIUM/HIGH)")
    suggestions: List[str] = Field(default_factory=list, description="Optimization suggestions")

    class Config:
        from_attributes = True


class QueryExecutionResult(BaseModel):
    """Query execution result"""
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    row_count: int = Field(..., description="Number of rows returned")
    columns: List[Dict[str, str]] = Field(..., description="Column information")
    data: List[Dict[str, Any]] = Field(..., description="Query result data")
    has_more: bool = Field(False, description="Whether there are more results")
    total_rows: Optional[int] = Field(None, description="Total rows (if available)")

    class Config:
        from_attributes = True


class RAGSQLResult(BaseModel):
    """Complete RAG-SQL processing result"""
    tenant_id: str = Field(..., description="Tenant ID")
    original_query: str = Field(..., description="Original natural language query")
    generated_sql: str = Field(..., description="Generated SQL query")
    validation_result: SQLValidationResult = Field(..., description="SQL validation result")
    execution_result: QueryExecutionResult = Field(..., description="Query execution result")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    correction_attempts: int = Field(default=0, description="Number of correction attempts")
    explanation: str = Field(..., description="Explanation of the result")
    confidence_score: float = Field(..., description="Overall confidence score")
    processing_steps: List[str] = Field(default_factory=list, description="Processing steps taken")

    class Config:
        from_attributes = True


class DatabaseConnection(BaseModel):
    """Database connection model for tenant isolation"""
    tenant_id: str = Field(..., description="Tenant ID")
    connection_id: int = Field(..., description="Data source connection ID")
    connection_string: str = Field(..., description="Database connection string")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, description="Connection timeout in seconds")
    is_active: bool = Field(default=True, description="Whether connection is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")

    class Config:
        from_attributes = True


class RAGSQLStats(BaseModel):
    """RAG-SQL processing statistics"""
    tenant_id: str = Field(..., description="Tenant ID")
    total_queries: int = Field(default=0, description="Total number of queries processed")
    successful_queries: int = Field(default=0, description="Number of successful queries")
    failed_queries: int = Field(default=0, description="Number of failed queries")
    average_processing_time_ms: float = Field(default=0, description="Average processing time")
    average_execution_time_ms: float = Field(default=0, description="Average execution time")
    most_queried_tables: List[str] = Field(default_factory=list, description="Most queried tables")
    query_types: Dict[str, int] = Field(default_factory=dict, description="Query type distribution")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True