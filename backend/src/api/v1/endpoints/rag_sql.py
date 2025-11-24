"""
RAG-SQL API endpoints for Data Agent V4 Backend
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...services.rag_sql_service import RAGSQLService
from ...services.database_schema_service import DatabaseSchemaService
from ...services.sql_execution_service import SQLExecutionService
from ...models.rag_sql import (
    RAGSQLResult,
    DatabaseSchema,
    RAGSQLStats,
    SQLQuery,
    SQLValidationResult,
)
from ...core.security import get_current_tenant
from ...core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
rag_sql_service = RAGSQLService()
schema_service = DatabaseSchemaService()
sql_executor = SQLExecutionService()


# Pydantic models for request/response
class NaturalLanguageQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query", min_length=1, max_length=1000)
    connection_id: int = Field(..., description="Data source connection ID")
    force_refresh: bool = Field(False, description="Force refresh schema cache")
    enable_cache: bool = Field(True, description="Enable query result caching")


class SQLValidationRequest(BaseModel):
    query: str = Field(..., description="SQL query to validate")
    connection_id: int = Field(..., description="Data source connection ID")


class SQLExecutionRequest(BaseModel):
    query: str = Field(..., description="SQL query to execute")
    parameters: List[Any] = Field(default_factory=list, description="Query parameters")
    connection_id: int = Field(..., description="Data source connection ID")
    timeout: Optional[int] = Field(None, description="Query timeout in seconds")


class SchemaDiscoveryRequest(BaseModel):
    connection_id: int = Field(..., description="Data source connection ID")
    force_refresh: bool = Field(False, description="Force refresh schema cache")


class ConnectionTestRequest(BaseModel):
    connection_id: int = Field(..., description="Data source connection ID")


@router.post("/query", response_model=RAGSQLResult)
async def process_natural_language_query(
    request: NaturalLanguageQueryRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Process natural language query through RAG-SQL chain

    This endpoint converts natural language queries to SQL and executes them
    with full tenant isolation and safety validation.
    """
    try:
        # Get connection string for tenant (this would come from your data source management)
        connection_string = await _get_connection_string(tenant_id, request.connection_id)

        if not connection_string:
            raise HTTPException(
                status_code=404,
                detail=f"Data source connection {request.connection_id} not found"
            )

        # Process query through RAG-SQL chain
        result = await rag_sql_service.process_natural_language_query(
            query=request.query,
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string,
            force_refresh=request.force_refresh,
            enable_cache=request.enable_cache
        )

        # Log successful query processing
        logger.info(f"Successfully processed query for tenant {tenant_id}: {request.query[:100]}...")

        return result

    except ValueError as e:
        logger.error(f"Query validation error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query processing error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during query processing")


@router.post("/schema/discover", response_model=DatabaseSchema)
async def discover_database_schema(
    request: SchemaDiscoveryRequest,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Discover database schema for a tenant connection

    This endpoint analyzes the connected database and returns detailed
    schema information including tables, columns, and relationships.
    """
    try:
        # Get connection string
        connection_string = await _get_connection_string(tenant_id, request.connection_id)

        if not connection_string:
            raise HTTPException(
                status_code=404,
                detail=f"Data source connection {request.connection_id} not found"
            )

        # Discover schema
        schema = await schema_service.discover_tenant_schema(
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string,
            force_refresh=request.force_refresh
        )

        logger.info(f"Schema discovery completed for tenant {tenant_id}, connection {request.connection_id}")
        return schema

    except Exception as e:
        logger.error(f"Schema discovery error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to discover database schema")


@router.post("/sql/validate", response_model=SQLValidationResult)
async def validate_sql_query(
    request: SQLValidationRequest,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Validate SQL query for security and correctness

    This endpoint checks SQL queries for dangerous operations,
    injection vulnerabilities, and syntax errors.
    """
    try:
        # Get connection string
        connection_string = await _get_connection_string(tenant_id, request.connection_id)

        if not connection_string:
            raise HTTPException(
                status_code=404,
                detail=f"Data source connection {request.connection_id} not found"
            )

        # Get schema for validation context
        schema = await schema_service.discover_tenant_schema(
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string
        )

        # Create SQL query object
        sql_query = SQLQuery(query=request.query)

        # Validate query
        validation_result = await rag_sql_service.sql_validator.validate_sql(
            sql_query=sql_query,
            schema=schema,
            tenant_id=tenant_id
        )

        logger.info(f"SQL validation completed for tenant {tenant_id}: {validation_result.is_valid}")
        return validation_result

    except Exception as e:
        logger.error(f"SQL validation error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate SQL query")


@router.post("/connection/test")
async def test_database_connection(
    request: ConnectionTestRequest,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Test database connection for a tenant

    This endpoint verifies that a tenant's database connection
    is working and returns connection information.
    """
    try:
        # Get connection string
        connection_string = await _get_connection_string(tenant_id, request.connection_id)

        if not connection_string:
            raise HTTPException(
                status_code=404,
                detail=f"Data source connection {request.connection_id} not found"
            )

        # Test connection
        test_result = await sql_executor.test_connection(
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string
        )

        logger.info(f"Connection test completed for tenant {tenant_id}, connection {request.connection_id}")
        return test_result

    except Exception as e:
        logger.error(f"Connection test error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test database connection")


@router.post("/sql/execute")
async def execute_sql_query(
    request: SQLExecutionRequest,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Execute SQL query directly (with validation)

    This endpoint executes SQL queries directly after validation.
    Use with caution - this bypasses the natural language processing.
    """
    try:
        # Get connection string
        connection_string = await _get_connection_string(tenant_id, request.connection_id)

        if not connection_string:
            raise HTTPException(
                status_code=404,
                detail=f"Data source connection {request.connection_id} not found"
            )

        # Create SQL query object
        sql_query = SQLQuery(
            query=request.query,
            parameters=request.parameters
        )

        # Get schema for validation
        schema = await schema_service.discover_tenant_schema(
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string
        )

        # Validate query first
        validation_result = await rag_sql_service.sql_validator.validate_sql(
            sql_query=sql_query,
            schema=schema,
            tenant_id=tenant_id
        )

        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "SQL validation failed",
                    "validation_errors": validation_result.validation_errors,
                    "security_warnings": validation_result.security_warnings
                }
            )

        # Execute query
        execution_result = await sql_executor.execute_query(
            sql_query=sql_query,
            tenant_id=tenant_id,
            connection_id=request.connection_id,
            connection_string=connection_string,
            timeout=request.timeout
        )

        logger.info(f"SQL query executed for tenant {tenant_id}")
        return execution_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL execution error for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to execute SQL query")


@router.get("/stats/{tenant_id}", response_model=RAGSQLStats)
async def get_rag_sql_stats(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """
    Get RAG-SQL processing statistics for a tenant

    This endpoint returns usage statistics and performance metrics
    for the RAG-SQL processing service.
    """
    # Verify tenant access
    if tenant_id != current_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        stats = await rag_sql_service.get_stats(tenant_id)

        if not stats:
            # Return empty stats if no data exists
            stats = RAGSQLStats(
                tenant_id=tenant_id,
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                average_processing_time_ms=0.0,
                average_execution_time_ms=0.0,
                most_queried_tables=[],
                query_types={}
            )

        return stats

    except Exception as e:
        logger.error(f"Error getting stats for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.delete("/cache/{tenant_id}")
async def clear_tenant_cache(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """
    Clear cache for a specific tenant

    This endpoint clears all cached queries and schemas for a tenant.
    """
    # Verify tenant access
    if tenant_id != current_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        await rag_sql_service.clear_cache(tenant_id=tenant_id)

        logger.info(f"Cache cleared for tenant {tenant_id}")
        return {"message": f"Cache cleared for tenant {tenant_id}"}

    except Exception as e:
        logger.error(f"Error clearing cache for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/health")
async def get_rag_sql_health():
    """
    Get RAG-SQL service health status

    This endpoint returns the current health and status of all
    RAG-SQL service components.
    """
    try:
        health_status = await rag_sql_service.get_health_status()
        return health_status

    except Exception as e:
        logger.error(f"Error getting RAG-SQL health status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/queries/active/{tenant_id}")
async def get_active_queries(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """
    Get active queries for a tenant

    This endpoint returns currently running queries for monitoring.
    """
    # Verify tenant access
    if tenant_id != current_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Get connection string
        connection_string = await _get_connection_string(tenant_id, None)  # Need any connection

        if not connection_string:
            return {"active_queries": []}

        # Get active queries
        active_queries = await sql_executor.get_active_queries(
            tenant_id=tenant_id,
            connection_id=0,  # Placeholder
            connection_string=connection_string
        )

        return {"active_queries": active_queries}

    except Exception as e:
        logger.error(f"Error getting active queries for tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active queries")


# Helper function to get connection string
async def _get_connection_string(tenant_id: str, connection_id: int) -> Optional[str]:
    """
    Get encrypted connection string for tenant data source

    This is a placeholder function - in a real implementation,
    you would retrieve this from your data sources table.
    """
    # TODO: Implement actual data source retrieval
    # This should query your data_sources table for the tenant
    # and return the encrypted connection string

    # For now, return None to indicate the implementation is needed
    logger.warning(f"Connection string retrieval not implemented for tenant {tenant_id}, connection {connection_id}")
    return None