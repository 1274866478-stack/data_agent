"""
SQL Execution Service for Data Agent V4 Backend
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncpg
import json
from cryptography.fernet import Fernet

from ..models.rag_sql import (
    SQLQuery,
    QueryExecutionResult,
    DatabaseConnection,
    RAGSQLStats,
)
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SQLExecutionService:
    """Service for executing SQL queries with tenant isolation"""

    def __init__(self):
        self.connection_pools: Dict[str, asyncpg.Pool] = {}
        self.pool_timeout = 30
        self.query_timeout = 30  # Default query timeout in seconds
        self.max_result_rows = 10000  # Maximum rows to return
        self.cipher_suite = Fernet(settings.encryption_key.encode() if settings.encryption_key else Fernet.generate_key())

        # Statistics tracking
        self.stats_cache: Dict[str, RAGSQLStats] = {}

    async def execute_query(
        self,
        sql_query: SQLQuery,
        tenant_id: str,
        connection_id: int,
        connection_string: str,
        timeout: Optional[int] = None
    ) -> QueryExecutionResult:
        """
        Execute SQL query with tenant isolation

        Args:
            sql_query: SQL query to execute
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string
            timeout: Query timeout in seconds

        Returns:
            QueryExecutionResult: Query execution result
        """
        start_time = datetime.utcnow()
        pool_key = f"{tenant_id}:{connection_id}"

        try:
            # Get connection pool
            pool = await self._get_connection_pool(pool_key, connection_string)

            # Set timeout
            query_timeout = timeout or self.query_timeout

            # Execute query with timeout
            async with asyncio.timeout(query_timeout):
                result = await self._execute_query_with_pool(
                    pool, sql_query, tenant_id, connection_id
                )

            # Calculate execution time
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Update statistics
            await self._update_stats(tenant_id, True, execution_time, result.row_count)

            logger.info(f"Query executed successfully for tenant {tenant_id} in {execution_time}ms")
            return result

        except asyncio.TimeoutError:
            await self._update_stats(tenant_id, False, 0, 0)
            logger.error(f"Query timeout for tenant {tenant_id}")
            raise Exception(f"Query execution timeout after {query_timeout} seconds")

        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self._update_stats(tenant_id, False, execution_time, 0)
            logger.error(f"Query execution failed for tenant {tenant_id}: {str(e)}")
            raise Exception(f"Query execution failed: {str(e)}")

    async def _get_connection_pool(
        self,
        pool_key: str,
        connection_string: str
    ) -> asyncpg.Pool:
        """Get or create connection pool for tenant"""
        if pool_key not in self.connection_pools:
            # Decrypt connection string
            decrypted_connection = self._decrypt_connection_string(connection_string)

            # Create connection pool
            pool = await asyncpg.create_pool(
                decrypted_connection,
                min_size=2,
                max_size=10,
                command_timeout=self.pool_timeout,
                server_settings={
                    'application_name': 'data_agent_v4',
                    'timezone': 'UTC'
                }
            )
            self.connection_pools[pool_key] = pool

        return self.connection_pools[pool_key]

    async def _execute_query_with_pool(
        self,
        pool: asyncpg.Pool,
        sql_query: SQLQuery,
        tenant_id: str,
        connection_id: int
    ) -> QueryExecutionResult:
        """Execute query using connection pool"""
        start_time = datetime.utcnow()

        async with pool.acquire() as conn:
            # Set query parameters
            await conn.set_builtin_type_codec(
                'json',
                codec_name='json'
            )

            # Execute query
            if sql_query.parameters:
                result = await conn.fetch(
                    sql_query.query,
                    *sql_query.parameters,
                    timeout=self.query_timeout
                )
            else:
                result = await conn.fetch(
                    sql_query.query,
                    timeout=self.query_timeout
                )

            # Convert to result format
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if not result:
                # Empty result set
                return QueryExecutionResult(
                    execution_time_ms=execution_time,
                    row_count=0,
                    columns=[],
                    data=[],
                    has_more=False,
                    total_rows=0
                )

            # Extract column information
            columns = [
                {
                    'name': col,
                    'type': self._get_column_type(result[0], col)
                }
                for col in result[0].keys()
            ]

            # Convert data rows
            data = []
            for row in result:
                row_dict = dict(row)
                # Process each value
                for key, value in row_dict.items():
                    row_dict[key] = self._process_value(value)
                data.append(row_dict)

            # Apply result limit
            has_more = len(data) > self.max_result_rows
            if has_more:
                data = data[:self.max_result_rows]

            return QueryExecutionResult(
                execution_time_ms=execution_time,
                row_count=len(data),
                columns=columns,
                data=data,
                has_more=has_more,
                total_rows=len(data)  # Would need COUNT query for exact total
            )

    def _get_column_type(self, row: dict, column_name: str) -> str:
        """Get column type from value"""
        if column_name not in row:
            return 'unknown'

        value = row[column_name]
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, datetime):
            return 'datetime'
        elif isinstance(value, dict) or isinstance(value, list):
            return 'json'
        else:
            return 'unknown'

    def _process_value(self, value: Any) -> Any:
        """Process database value for JSON serialization"""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value)
        else:
            return value

    def _decrypt_connection_string(self, encrypted_string: str) -> str:
        """Decrypt database connection string"""
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_string.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt connection string: {str(e)}")
            raise ValueError("Invalid connection string")

    async def test_connection(
        self,
        tenant_id: str,
        connection_id: int,
        connection_string: str
    ) -> Dict[str, Any]:
        """
        Test database connection

        Args:
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string

        Returns:
            Dict containing connection test results
        """
        pool_key = f"{tenant_id}:{connection_id}"
        start_time = datetime.utcnow()

        try:
            # Get connection pool
            pool = await self._get_connection_pool(pool_key, connection_string)

            # Test simple query
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1 as test")
                version = await conn.fetchval("SELECT version()")
                database_name = await conn.fetchval("SELECT current_database()")

            connection_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return {
                'success': True,
                'connection_time_ms': connection_time,
                'database_name': database_name,
                'version': version,
                'message': 'Connection successful'
            }

        except Exception as e:
            connection_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Connection test failed for tenant {tenant_id}: {str(e)}")

            return {
                'success': False,
                'connection_time_ms': connection_time,
                'error': str(e),
                'message': 'Connection failed'
            }

    async def explain_query(
        self,
        sql_query: SQLQuery,
        tenant_id: str,
        connection_id: int,
        connection_string: str
    ) -> Dict[str, Any]:
        """
        Get query execution plan

        Args:
            sql_query: SQL query to explain
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string

        Returns:
            Dict containing execution plan
        """
        pool_key = f"{tenant_id}:{connection_id}"

        try:
            pool = await self._get_connection_pool(pool_key, connection_string)

            async with pool.acquire() as conn:
                # Get execution plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql_query.query}"

                if sql_query.parameters:
                    plan_result = await conn.fetchval(explain_query, *sql_query.parameters)
                else:
                    plan_result = await conn.fetchval(explain_query)

                # Get cost estimate without execution
                cost_query = f"EXPLAIN (FORMAT JSON) {sql_query.query}"
                if sql_query.parameters:
                    cost_result = await conn.fetchval(cost_query, *sql_query.parameters)
                else:
                    cost_result = await conn.fetchval(cost_query)

                return {
                    'execution_plan': plan_result,
                    'cost_estimate': cost_result,
                    'query': sql_query.query
                }

        except Exception as e:
            logger.error(f"Failed to explain query for tenant {tenant_id}: {str(e)}")
            raise Exception(f"Failed to get execution plan: {str(e)}")

    async def cancel_query(
        self,
        tenant_id: str,
        connection_id: int,
        query_pid: int
    ) -> bool:
        """
        Cancel running query

        Args:
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            query_pid: Process ID of query to cancel

        Returns:
            bool: True if query was cancelled
        """
        pool_key = f"{tenant_id}:{connection_id}"

        try:
            pool = await self._get_connection_pool(pool_key, "")  # Need connection string

            async with pool.acquire() as conn:
                # Cancel query
                await conn.execute(f"SELECT pg_cancel_backend({query_pid})")
                return True

        except Exception as e:
            logger.error(f"Failed to cancel query {query_pid} for tenant {tenant_id}: {str(e)}")
            return False

    async def get_active_queries(
        self,
        tenant_id: str,
        connection_id: int,
        connection_string: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of active queries for tenant

        Args:
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string

        Returns:
            List of active queries
        """
        pool_key = f"{tenant_id}:{connection_id}"

        try:
            pool = await self._get_connection_pool(pool_key, connection_string)

            async with pool.acquire() as conn:
                # Query pg_stat_activity for active queries
                query = """
                    SELECT pid, now() - query_start AS duration, query, state, wait_event_type, wait_event
                    FROM pg_stat_activity
                    WHERE state = 'active' AND query != '<IDLE>'
                    ORDER BY query_start
                """

                results = await conn.fetch(query)

                active_queries = []
                for row in results:
                    active_queries.append({
                        'pid': row['pid'],
                        'duration': str(row['duration']),
                        'query': row['query'],
                        'state': row['state'],
                        'wait_event_type': row['wait_event_type'],
                        'wait_event': row['wait_event']
                    })

                return active_queries

        except Exception as e:
            logger.error(f"Failed to get active queries for tenant {tenant_id}: {str(e)}")
            return []

    async def _update_stats(
        self,
        tenant_id: str,
        success: bool,
        execution_time_ms: int,
        row_count: int
    ):
        """Update execution statistics"""
        if tenant_id not in self.stats_cache:
            self.stats_cache[tenant_id] = RAGSQLStats(
                tenant_id=tenant_id,
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                average_processing_time_ms=0.0,
                average_execution_time_ms=0.0,
                most_queried_tables=[],
                query_types={}
            )

        stats = self.stats_cache[tenant_id]
        stats.total_queries += 1

        if success:
            stats.successful_queries += 1

            # Update average times
            total_successful = stats.successful_queries
            stats.average_execution_time_ms = (
                (stats.average_execution_time_ms * (total_successful - 1) + execution_time_ms) / total_successful
            )
        else:
            stats.failed_queries += 1

        stats.last_updated = datetime.utcnow()

    async def get_stats(self, tenant_id: str) -> Optional[RAGSQLStats]:
        """Get execution statistics for tenant"""
        return self.stats_cache.get(tenant_id)

    async def reset_stats(self, tenant_id: str):
        """Reset execution statistics for tenant"""
        if tenant_id in self.stats_cache:
            del self.stats_cache[tenant_id]

    async def close_connection_pools(self):
        """Close all connection pools"""
        for pool_key, pool in self.connection_pools.items():
            try:
                await pool.close()
                logger.info(f"Closed connection pool: {pool_key}")
            except Exception as e:
                logger.error(f"Error closing connection pool {pool_key}: {str(e)}")

        self.connection_pools.clear()

    async def cleanup_idle_connections(self):
        """Clean up idle connection pools"""
        current_time = datetime.utcnow()
        pools_to_close = []

        for pool_key, pool in self.connection_pools.items():
            try:
                # Check if pool has idle connections
                pool_stats = pool.get_size()
                if pool_stats.idle > 0:
                    # Could implement more sophisticated cleanup logic based on last usage
                    pass
            except Exception as e:
                logger.error(f"Error checking pool {pool_key}: {str(e)}")
                pools_to_close.append(pool_key)

        # Close problematic pools
        for pool_key in pools_to_close:
            try:
                await self.connection_pools[pool_key].close()
                del self.connection_pools[pool_key]
                logger.info(f"Cleaned up connection pool: {pool_key}")
            except Exception as e:
                logger.error(f"Error cleaning up pool {pool_key}: {str(e)}")

    async def get_connection_pool_info(self, tenant_id: str, connection_id: int) -> Dict[str, Any]:
        """Get information about connection pool"""
        pool_key = f"{tenant_id}:{connection_id}"

        if pool_key not in self.connection_pools:
            return {'status': 'not_created'}

        pool = self.connection_pools[pool_key]
        try:
            size = pool.get_size()
            return {
                'status': 'active',
                'size': size.size,
                'min_size': size.min_size,
                'max_size': size.max_size,
                'idle_connections': size.idle,
                'active_connections': size.size - size.idle
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    async def validate_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """
        Validate database connection string format

        Args:
            connection_string: Encrypted database connection string

        Returns:
            Dict containing validation result
        """
        try:
            # Decrypt connection string
            decrypted_connection = self._decrypt_connection_string(connection_string)

            # Basic validation for PostgreSQL connection string
            required_parts = ['postgresql://', 'host', 'port', 'dbname', 'user']

            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }

            for part in required_parts:
                if part not in decrypted_connection.lower() and part != 'postgresql://':
                    if part == 'postgresql://':
                        validation_result['errors'].append('Connection string must start with postgresql://')
                    else:
                        validation_result['warnings'].append(f'Connection string may be missing {part}')

            # Check for SSL configuration
            if 'sslmode=' not in decrypted_connection.lower():
                validation_result['warnings'].append('Consider specifying SSL mode for secure connection')

            # Try to parse connection parameters
            try:
                # Simple regex to extract connection parameters
                import re

                # Extract host
                host_match = re.search(r'host=([^;:\s]+)', decrypted_connection)
                if host_match:
                    host = host_match.group(1)
                    if host in ['localhost', '127.0.0.1']:
                        validation_result['warnings'].append('Using localhost - ensure database is accessible')

                # Extract port
                port_match = re.search(r'port=(\d+)', decrypted_connection)
                if port_match:
                    port = int(port_match.group(1))
                    if port < 1024 or port > 65535:
                        validation_result['errors'].append(f'Invalid port number: {port}')

            except Exception as e:
                validation_result['warnings'].append(f'Could not parse connection parameters: {str(e)}')

            validation_result['is_valid'] = len(validation_result['errors']) == 0
            return validation_result

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'Connection string validation failed: {str(e)}'],
                'warnings': []
            }