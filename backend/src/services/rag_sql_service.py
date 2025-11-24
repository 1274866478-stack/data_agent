"""
RAG-SQL Chain Integration Service for Data Agent V4 Backend
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import json

from .database_schema_service import DatabaseSchemaService
from .query_analyzer import QueryAnalyzer
from .sql_generator import SQLGenerator
from .sql_validator import SQLValidator
from .sql_execution_service import SQLExecutionService
from .cache_service import CacheFactory, TenantCacheKeyGenerator
from .performance_monitor import performance_monitor
from .query_performance_monitor import performance_monitor as query_perf_monitor
from ..models.rag_sql import (
    QueryIntent,
    SQLQuery,
    SQLValidationResult,
    QueryExecutionResult,
    RAGSQLResult,
    DatabaseSchema,
    RAGSQLStats,
    QueryType,
)
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGSQLService:
    """RAG-SQL processing chain service"""

    def __init__(self, cache_type: str = None, use_ai: bool = True):
        # Initialize component services
        self.schema_service = DatabaseSchemaService()
        self.query_analyzer = QueryAnalyzer()
        self.sql_generator = SQLGenerator(use_ai=use_ai)
        self.sql_validator = SQLValidator()
        self.sql_executor = SQLExecutionService()

        # Initialize cache service - use config or parameter
        cache_type = cache_type or settings.cache_type or 'memory'
        self.cache = CacheFactory.create_cache(cache_type)
        self.cache_ttl = timedelta(hours=1)

        logger.info(f"RAG-SQL服务初始化完成 - AI模式: {'启用' if use_ai else '禁用'}, 缓存类型: {cache_type}")

        # 启动性能监控
        query_perf_monitor.start_monitoring()

        # Statistics cache (still use local memory for now)
        self.stats_cache: Dict[str, RAGSQLStats] = {}

        # Self-correction configuration
        self.max_correction_attempts = 3
        self.correction_strategies = [
            'simplify_query',
            'add_where_clause',
            'fix_column_names',
            'adjust_aggregations',
            'reduce_complexity'
        ]

    async def process_natural_language_query(
        self,
        query: str,
        tenant_id: str,
        connection_id: int,
        connection_string: str,
        force_refresh: bool = False,
        enable_cache: bool = True
    ) -> RAGSQLResult:
        """
        Process natural language query through RAG-SQL chain

        Args:
            query: Natural language query
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string
            force_refresh: Force refresh schema cache
            enable_cache: Enable query result caching

        Returns:
            RAGSQLResult: Complete processing result
        """
        import uuid
        query_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        processing_steps = []

        # 开始性能监控
        async with query_perf_monitor.monitor_query(query_id, tenant_id, "rag_sql_query") as metrics:
            try:
                # Check cache first
                if enable_cache and not force_refresh:
                    cached_result = await self._get_cached_result(query, tenant_id, connection_id)
                    if cached_result:
                        processing_steps.append("Returned cached result")
                        metrics.cache_hit = True
                        return cached_result

                # Step 1: Database Structure Discovery
                step_start = time.time()
                processing_steps.append("Discovering database schema")
                schema = await self._get_or_discover_schema(
                    tenant_id, connection_id, connection_string, force_refresh
                )
                schema_time = time.time() - step_start

                # Step 2: Query Intent Analysis
                step_start = time.time()
                processing_steps.append("Analyzing query intent")
                intent = await self.query_analyzer.analyze_query_intent(query, schema)
                analysis_time = time.time() - step_start

                # Check if analysis confidence is sufficient
                if intent.confidence_score < 0.3:
                    raise ValueError(f"Query analysis confidence too low: {intent.confidence_score}")

                # Step 3: SQL Generation
                step_start = time.time()
                processing_steps.append("Generating SQL query")
                sql_query = await self.sql_generator.generate_sql(intent, schema, natural_query=query)
                metrics.sql_generation_time = time.time() - step_start

                # Step 4: SQL Validation
                step_start = time.time()
                processing_steps.append("Validating SQL query")
                validation_result = await self.sql_validator.validate_sql(sql_query, schema, tenant_id)
                metrics.sql_validation_time = time.time() - step_start

                if not validation_result.is_valid:
                    # Try self-correction
                    corrected_query, corrected_validation = await self._attempt_sql_correction(
                        query, intent, schema, tenant_id, sql_query, validation_result
                    )
                    sql_query = corrected_query
                    validation_result = corrected_validation

                # Step 5: Query Execution
                step_start = time.time()
                processing_steps.append("Executing SQL query")
                execution_result = await self.sql_executor.execute_query(
                    sql_query, tenant_id, connection_id, connection_string
                )
                metrics.execution_time = time.time() - step_start

                # Step 6: Result Processing
                step_start = time.time()
                processing_steps.append("Processing query results")
                processed_result = await self._process_query_result(
                    query, intent, sql_query, execution_result
                )
                metrics.result_processing_time = time.time() - step_start
                metrics.row_count = len(execution_result.data) if execution_result.data else 0

                # Step 7: Self-Correction (if needed)
                if not execution_result.data and validation_result.risk_level != "HIGH":
                    processing_steps.append("Attempting self-correction")
                    corrected_result = await self._attempt_result_correction(
                        query, intent, schema, tenant_id, connection_id, connection_string,
                        sql_query, validation_result, execution_result
                    )
                    if corrected_result:
                        processed_result = corrected_result

                # Calculate total processing time
                total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Generate explanation
                explanation = await self._generate_explanation(
                    query, intent, sql_query, execution_result, processing_steps
                )

                # Create final result
                result = RAGSQLResult(
                    tenant_id=tenant_id,
                    original_query=query,
                    generated_sql=sql_query.query,
                    validation_result=validation_result,
                    execution_result=execution_result,
                    processing_time_ms=total_time,
                    correction_attempts=0,  # Will be updated if corrections were made
                    explanation=explanation,
                    confidence_score=intent.confidence_score,
                    processing_steps=processing_steps
                )

                # Cache result
                if enable_cache:
                    await self._cache_result(query, tenant_id, connection_id, result)

                # Update statistics
                await self._update_stats(tenant_id, intent, sql_query, execution_result, total_time)

                # 记录性能指标
                query_info = {
                    "tenant_id": tenant_id,
                    "query": query,
                    "query_type": "SELECT",
                    "table_names": intent.target_tables,
                    "cache_hit": False,
                    "error_occurred": False,
                    "parsing_time": 0,  # 可以从各个步骤获取更精确的时间
                    "execution_time": execution_result.execution_time_ms,
                    "rows_returned": execution_result.row_count,
                    "rows_examined": execution_result.row_count  # 简化处理
                }

                await performance_monitor.finish_query_monitoring(monitoring_context, query_info)

                logger.info(f"RAG-SQL processing completed for tenant {tenant_id} in {total_time}ms")
                return result

            except Exception as e:
                total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                error_message = str(e)
                logger.error(f"RAG-SQL processing failed for tenant {tenant_id}: {error_message}")

                # 记录错误性能指标
                try:
                    error_query_info = {
                        "tenant_id": tenant_id,
                        "query": query,
                        "query_type": "SELECT",
                        "table_names": [],
                        "cache_hit": False,
                        "error_occurred": True,
                        "error_message": error_message,
                        "parsing_time": 0,
                        "execution_time": 0,
                        "rows_returned": 0,
                        "rows_examined": 0
                    }

                    await performance_monitor.finish_query_monitoring(monitoring_context, error_query_info)
                except Exception as monitor_error:
                    logger.warning(f"记录错误性能指标失败: {monitor_error}")

                # Return error result
                return RAGSQLResult(
                    tenant_id=tenant_id,
                    original_query=query,
                    generated_sql="",
                    validation_result=SQLValidationResult(
                        is_valid=False,
                        validation_errors=[error_message],
                        security_warnings=[],
                        risk_level="HIGH",
                        suggestions=["Check query syntax and database connection"]
                    ),
                    execution_result=QueryExecutionResult(
                        execution_time_ms=total_time,
                        row_count=0,
                        columns=[],
                        data=[],
                        has_more=False
                    ),
                    processing_time_ms=total_time,
                    correction_attempts=0,
                    explanation=f"Error: {error_message}",
                    confidence_score=0.0,
                    processing_steps=processing_steps
                )

    async def _get_or_discover_schema(
        self,
        tenant_id: str,
        connection_id: int,
        connection_string: str,
        force_refresh: bool = False
    ) -> DatabaseSchema:
        """Get cached schema or discover new one"""
        cache_key = TenantCacheKeyGenerator.schema(tenant_id, connection_id)

        if not force_refresh:
            cached_schema = await self.cache.get(cache_key)
            if cached_schema:
                # Check if cache is still valid
                if datetime.utcnow() - cached_schema.discovered_at < self.cache_ttl:
                    return cached_schema

        # Discover new schema
        schema = await self.schema_service.discover_tenant_schema(
            tenant_id, connection_id, connection_string, force_refresh
        )

        # Cache schema
        ttl = int(self.cache_ttl.total_seconds())
        await self.cache.set(cache_key, schema, ttl)

        return schema

    async def _attempt_sql_correction(
        self,
        original_query: str,
        intent: QueryIntent,
        schema: DatabaseSchema,
        tenant_id: str,
        sql_query: SQLQuery,
        validation_result: SQLValidationResult
    ) -> Tuple[SQLQuery, SQLValidationResult]:
        """Attempt to correct SQL validation errors"""
        corrected_query = sql_query
        corrected_validation = validation_result

        for attempt in range(self.max_correction_attempts):
            try:
                # Apply correction strategy
                strategy = self.correction_strategies[attempt % len(self.correction_strategies)]

                if strategy == 'simplify_query':
                    corrected_query = await self._simplify_query(corrected_query, intent)
                elif strategy == 'add_where_clause':
                    corrected_query = await self._add_where_clause(corrected_query, intent, schema)
                elif strategy == 'fix_column_names':
                    corrected_query = await self._fix_column_names(corrected_query, intent, schema)
                elif strategy == 'adjust_aggregations':
                    corrected_query = await self._adjust_aggregations(corrected_query, intent)
                elif strategy == 'reduce_complexity':
                    corrected_query = await self._reduce_complexity(corrected_query, intent)

                # Validate corrected query
                new_validation = await self.sql_validator.validate_sql(
                    corrected_query, schema, tenant_id
                )

                if new_validation.is_valid or new_validation.risk_level < validation_result.risk_level:
                    corrected_validation = new_validation
                    logger.info(f"SQL correction successful on attempt {attempt + 1} using {strategy}")
                    break

            except Exception as e:
                logger.warning(f"SQL correction attempt {attempt + 1} failed: {str(e)}")
                continue

        return corrected_query, corrected_validation

    async def _attempt_result_correction(
        self,
        original_query: str,
        intent: QueryIntent,
        schema: DatabaseSchema,
        tenant_id: str,
        connection_id: int,
        connection_string: str,
        sql_query: SQLQuery,
        validation_result: SQLValidationResult,
        execution_result: QueryExecutionResult
    ) -> Optional[RAGSQLResult]:
        """Attempt to correct empty or invalid results"""
        for attempt in range(self.max_correction_attempts):
            try:
                strategy = self.correction_strategies[attempt % len(self.correction_strategies)]

                # Generate alternative query
                if strategy == 'simplify_query':
                    new_sql = await self._simplify_query(sql_query, intent)
                elif strategy == 'add_where_clause':
                    new_sql = await self._add_where_clause(sql_query, intent, schema)
                elif strategy == 'fix_column_names':
                    new_sql = await self._fix_column_names(sql_query, intent, schema)
                elif strategy == 'adjust_aggregations':
                    new_sql = await self._adjust_aggregations(sql_query, intent)
                elif strategy == 'reduce_complexity':
                    new_sql = await self._reduce_complexity(sql_query, intent)
                else:
                    continue

                # Validate new query
                new_validation = await self.sql_validator.validate_sql(new_sql, schema, tenant_id)

                if not new_validation.is_valid:
                    continue

                # Execute new query
                new_execution = await self.sql_executor.execute_query(
                    new_sql, tenant_id, connection_id, connection_string
                )

                # Check if we got results
                if new_execution.data:
                    logger.info(f"Result correction successful on attempt {attempt + 1} using {strategy}")

                    # Generate explanation for correction
                    explanation = await self._generate_explanation(
                        original_query, intent, new_sql, new_execution,
                        [f"Corrected using {strategy} strategy"]
                    )

                    return RAGSQLResult(
                        tenant_id=tenant_id,
                        original_query=original_query,
                        generated_sql=new_sql.query,
                        validation_result=new_validation,
                        execution_result=new_execution,
                        processing_time_ms=execution_result.execution_time_ms,
                        correction_attempts=attempt + 1,
                        explanation=explanation,
                        confidence_score=intent.confidence_score * 0.8,  # Reduce confidence for corrected queries
                        processing_steps=["Applied correction strategy", "Executed corrected query"]
                    )

            except Exception as e:
                logger.warning(f"Result correction attempt {attempt + 1} failed: {str(e)}")
                continue

        return None

    async def _simplify_query(self, sql_query: SQLQuery, intent: QueryIntent) -> SQLQuery:
        """Simplify complex query"""
        simplified = sql_query.query

        # Remove complex joins
        if 'JOIN' in simplified.upper() and intent.query_type != QueryType.JOIN:
            # Try to use only the main table
            main_table = intent.target_tables[0] if intent.target_tables else None
            if main_table:
                simplified = f"SELECT * FROM {main_table}"

        # Remove complex aggregations
        if intent.query_type == QueryType.SELECT and 'COUNT(' in simplified.upper():
            simplified = simplified.replace('COUNT(*)', '*')

        # Remove ORDER BY if not necessary
        if 'ORDER BY' in simplified.upper():
            # Keep ORDER BY only if explicitly requested
            order_indicators = ['order', 'sort', 'top', 'bottom', 'highest', 'lowest']
            if not any(indicator in intent.original_query.lower() for indicator in order_indicators):
                simplified = simplified.split('ORDER BY')[0].strip()

        return SQLQuery(
            query=simplified,
            parameters=sql_query.parameters,
            query_type=sql_query.query_type
        )

    async def _add_where_clause(self, sql_query: SQLQuery, intent: QueryIntent, schema: DatabaseSchema) -> SQLQuery:
        """Add WHERE clause if missing"""
        if 'WHERE' in sql_query.query.upper():
            return sql_query

        modified_query = sql_query.query

        # Add simple WHERE clause if conditions exist
        if intent.conditions:
            # For simplicity, add a basic condition
            main_table = intent.target_tables[0] if intent.target_tables else None
            if main_table and main_table in schema.tables:
                table_info = schema.tables[main_table]
                # Find a primary key column
                pk_column = next((col.name for col in table_info.columns if col.is_primary_key), None)
                if pk_column:
                    if 'LIMIT' in modified_query.upper():
                        modified_query = modified_query.replace('LIMIT', f'WHERE {pk_column} IS NOT NULL LIMIT')
                    else:
                        modified_query += f" WHERE {pk_column} IS NOT NULL"

        return SQLQuery(
            query=modified_query,
            parameters=sql_query.parameters,
            query_type=sql_query.query_type
        )

    async def _fix_column_names(self, sql_query: SQLQuery, intent: QueryIntent, schema: DatabaseSchema) -> SQLQuery:
        """Fix column name references"""
        modified_query = sql_query.query

        # Fix column references based on schema
        for table_name in intent.target_tables:
            if table_name in schema.tables:
                table_info = schema.tables[table_name]
                for column in table_info.columns:
                    # Replace approximate column names with exact ones
                    if column.name.lower() in modified_query.lower():
                        # Ensure table prefix is present
                        column_ref = f"{table_name}.{column.name}"
                        if column_ref not in modified_query:
                            modified_query = modified_query.replace(
                                column.name, column_ref
                            )

        return SQLQuery(
            query=modified_query,
            parameters=sql_query.parameters,
            query_type=sql_query.query_type
        )

    async def _adjust_aggregations(self, sql_query: SQLQuery, intent: QueryIntent) -> SQLQuery:
        """Adjust aggregation functions"""
        modified_query = sql_query.query

        # If query has aggregations but no GROUP BY, add GROUP BY
        if 'COUNT(' in modified_query.upper() or 'SUM(' in modified_query.upper():
            if 'GROUP BY' not in modified_query.upper():
                # Try to add a simple GROUP BY
                main_table = intent.target_tables[0] if intent.target_tables else None
                if main_table and intent.groupings:
                    group_by_clause = f" GROUP BY {intent.groupings[0]}"
                    if 'ORDER BY' in modified_query.upper():
                        modified_query = modified_query.replace('ORDER BY', group_by_clause + ' ORDER BY')
                    else:
                        modified_query += group_by_clause

        return SQLQuery(
            query=modified_query,
            parameters=sql_query.parameters,
            query_type=sql_query.query_type
        )

    async def _reduce_complexity(self, sql_query: SQLQuery, intent: QueryIntent) -> SQLQuery:
        """Reduce query complexity"""
        modified_query = sql_query.query

        # Remove subqueries
        if '(' in modified_query and modified_query.count('(') > 2:
            # Simplify to basic SELECT
            main_table = intent.target_tables[0] if intent.target_tables else 'table1'
            modified_query = f"SELECT * FROM {main_table}"

        # Reduce number of columns
        if 'SELECT *' in modified_query.upper():
            main_table = intent.target_tables[0] if intent.target_tables else 'table1'
            modified_query = f"SELECT id, name FROM {main_table}"

        return SQLQuery(
            query=modified_query,
            parameters=sql_query.parameters,
            query_type=QueryType.SELECT
        )

    async def _process_query_result(
        self,
        original_query: str,
        intent: QueryIntent,
        sql_query: SQLQuery,
        execution_result: QueryExecutionResult
    ) -> QueryExecutionResult:
        """Process and format query results"""
        if not execution_result.data:
            return execution_result

        # Convert data types and format values
        processed_data = []
        for row in execution_result.data:
            processed_row = {}
            for key, value in row.items():
                # Format dates
                if isinstance(value, str) and self._is_date_string(value):
                    processed_row[key] = self._format_date_string(value)
                else:
                    processed_row[key] = value
            processed_data.append(processed_row)

        # Calculate statistics if applicable
        if intent.query_type == QueryType.AGGREGATE and processed_data:
            # Add summary statistics
            summary_row = {}
            for column in execution_result.columns:
                if column['type'] in ['number', 'integer']:
                    values = [row.get(column['name']) for row in processed_data if row.get(column['name']) is not None]
                    if values:
                        summary_row[f"{column['name']}_sum"] = sum(values)
                        summary_row[f"{column['name']}_avg"] = sum(values) / len(values)
                        summary_row[f"{column['name']}_count"] = len(values)

            if summary_row:
                processed_data.append(summary_row)

        return QueryExecutionResult(
            execution_time_ms=execution_result.execution_time_ms,
            row_count=len(processed_data),
            columns=execution_result.columns,
            data=processed_data,
            has_more=execution_result.has_more,
            total_rows=execution_result.total_rows
        )

    def _is_date_string(self, value: str) -> bool:
        """Check if string represents a date"""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)

    def _format_date_string(self, value: str) -> str:
        """Format date string for display"""
        try:
            # Try to parse and reformat
            if 'T' in value:
                # ISO datetime
                return value
            else:
                # Date only
                return value
        except:
            return value

    async def _generate_explanation(
        self,
        original_query: str,
        intent: QueryIntent,
        sql_query: SQLQuery,
        execution_result: QueryExecutionResult,
        processing_steps: List[str]
    ) -> str:
        """Generate explanation of the query processing"""
        explanation_parts = []

        # Explain query understanding
        explanation_parts.append(f"Understood query as: {intent.query_type.value}")
        if intent.target_tables:
            explanation_parts.append(f"Target tables: {', '.join(intent.target_tables)}")

        # Explain SQL generation
        explanation_parts.append(f"Generated SQL: {sql_query.query}")

        # Explain execution results
        if execution_result.row_count > 0:
            explanation_parts.append(f"Returned {execution_result.row_count} rows")
        else:
            explanation_parts.append("No results found")

        # Explain processing steps
        if processing_steps:
            explanation_parts.append(f"Processing steps: {' → '.join(processing_steps)}")

        # Explain confidence
        confidence_desc = "high" if intent.confidence_score > 0.8 else "medium" if intent.confidence_score > 0.5 else "low"
        explanation_parts.append(f"Confidence: {confidence_desc} ({intent.confidence_score:.2f})")

        return " | ".join(explanation_parts)

    async def _get_cached_result(
        self,
        query: str,
        tenant_id: str,
        connection_id: int
    ) -> Optional[RAGSQLResult]:
        """Get cached result for query"""
        cache_key = TenantCacheKeyGenerator.query_result(tenant_id, connection_id, query)
        return await self.cache.get(cache_key)

    async def _cache_result(
        self,
        query: str,
        tenant_id: str,
        connection_id: int,
        result: RAGSQLResult
    ):
        """Cache query result"""
        cache_key = TenantCacheKeyGenerator.query_result(tenant_id, connection_id, query)
        ttl = int(self.cache_ttl.total_seconds())
        await self.cache.set(cache_key, result, ttl)

    
    async def _update_stats(
        self,
        tenant_id: str,
        intent: QueryIntent,
        sql_query: SQLQuery,
        execution_result: QueryExecutionResult,
        processing_time_ms: int
    ):
        """Update processing statistics"""
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

        if execution_result.row_count > 0:
            stats.successful_queries += 1
        else:
            stats.failed_queries += 1

        # Update averages
        stats.average_processing_time_ms = (
            (stats.average_processing_time_ms * (stats.total_queries - 1) + processing_time_ms) / stats.total_queries
        )

        stats.average_execution_time_ms = (
            (stats.average_execution_time_ms * (stats.total_queries - 1) + execution_result.execution_time_ms) / stats.total_queries
        )

        # Update most queried tables
        for table in intent.target_tables:
            if table not in stats.most_queried_tables:
                stats.most_queried_tables.append(table)
                # Keep only top 5 tables
                stats.most_queried_tables = stats.most_queried_tables[-5:]

        # Update query types
        query_type = intent.query_type.value
        if query_type not in stats.query_types:
            stats.query_types[query_type] = 0
        stats.query_types[query_type] += 1

        stats.last_updated = datetime.utcnow()

    async def get_stats(self, tenant_id: str) -> Optional[RAGSQLStats]:
        """Get processing statistics for tenant"""
        return self.stats_cache.get(tenant_id)

    async def clear_cache(self, tenant_id: Optional[str] = None):
        """Clear cache for specific tenant or all tenants"""
        if tenant_id:
            await self.cache.clear_tenant_cache(tenant_id)
        else:
            await self.cache.clear_all()

    async def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            'cache_size': await self.cache.get_size(),
            'cache_type': type(self.cache).__name__,
            'stats_cache_size': len(self.stats_cache),
            'active_tenants': len(self.stats_cache),
            'performance_monitor_buffer_size': performance_monitor.get_buffer_size(),
            'service_status': 'healthy',
            'last_updated': datetime.utcnow().isoformat()
        }

    async def get_performance_metrics(
        self,
        tenant_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取性能指标

        Args:
            tenant_id: 租户ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            List[Dict]: 性能指标列表
        """
        return await performance_monitor.get_tenant_metrics(
            tenant_id, start_time, end_time, limit
        )

    async def get_performance_summary(
        self,
        tenant_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取性能摘要

        Args:
            tenant_id: 租户ID
            days: 天数

        Returns:
            Dict: 性能摘要
        """
        return await performance_monitor.get_performance_summary(tenant_id, days)

    async def get_slow_queries(
        self,
        tenant_id: str,
        threshold_ms: float = 5000.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取慢查询

        Args:
            tenant_id: 租户ID
            threshold_ms: 慢查询阈值(毫秒)
            limit: 限制数量

        Returns:
            List[Dict]: 慢查询列表
        """
        return await performance_monitor.get_slow_queries(tenant_id, threshold_ms, limit)

    async def clear_performance_metrics(self, tenant_id: str):
        """清除租户性能指标"""
        await performance_monitor.clear_tenant_metrics(tenant_id)

    async def cleanup(self):
        """Cleanup resources"""
        await self.schema_service.close_connection_pools()
        await self.sql_executor.close_connection_pools()
        await self.cache.clear_all()
        self.stats_cache.clear()