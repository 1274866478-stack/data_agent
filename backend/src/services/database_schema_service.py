"""
Database Schema Discovery Service for Data Agent V4 Backend
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
import logging
from cryptography.fernet import Fernet
import json

from ..models.rag_sql import (
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
    DatabaseConnection,
)
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseSchemaService:
    """Service for discovering and caching database schemas"""

    def __init__(self):
        self.schema_cache: Dict[str, DatabaseSchema] = {}
        self.cache_ttl = timedelta(hours=1)  # Cache schema for 1 hour
        self.connection_pools: Dict[str, asyncpg.Pool] = {}
        self.cipher_suite = Fernet(settings.encryption_key.encode() if settings.encryption_key else Fernet.generate_key())

    async def discover_tenant_schema(
        self,
        tenant_id: str,
        connection_id: int,
        connection_string: str,
        force_refresh: bool = False
    ) -> DatabaseSchema:
        """
        Discover database schema for a tenant

        Args:
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string
            force_refresh: Force schema refresh

        Returns:
            DatabaseSchema: Complete database schema
        """
        cache_key = f"{tenant_id}:{connection_id}"

        # Check cache first
        if not force_refresh and cache_key in self.schema_cache:
            cached_schema = self.schema_cache[cache_key]
            if datetime.utcnow() - cached_schema.discovered_at < self.cache_ttl:
                logger.info(f"Using cached schema for tenant {tenant_id}")
                return cached_schema

        try:
            # Decrypt connection string
            decrypted_connection = self._decrypt_connection_string(connection_string)

            # Get database connection
            pool = await self._get_connection_pool(cache_key, decrypted_connection)

            # Discover schema
            schema = await self._discover_schema_with_connection(
                tenant_id, connection_id, pool
            )

            # Cache the schema
            self.schema_cache[cache_key] = schema

            logger.info(f"Discovered schema for tenant {tenant_id}: {len(schema.tables)} tables")
            return schema

        except Exception as e:
            logger.error(f"Failed to discover schema for tenant {tenant_id}: {str(e)}")
            raise

    async def _get_connection_pool(
        self,
        cache_key: str,
        connection_string: str
    ) -> asyncpg.Pool:
        """Get or create connection pool for database"""
        if cache_key not in self.connection_pools:
            pool = await asyncpg.create_pool(
                connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            self.connection_pools[cache_key] = pool
        return self.connection_pools[cache_key]

    async def _discover_schema_with_connection(
        self,
        tenant_id: str,
        connection_id: int,
        pool: asyncpg.Pool
    ) -> DatabaseSchema:
        """Discover schema using database connection"""

        async with pool.acquire() as conn:
            # Get database name
            database_name = await conn.fetchval("SELECT current_database()")

            # Get all tables
            tables_query = """
                SELECT table_name,
                       (SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            table_rows = await conn.fetch(tables_query)

            tables = {}
            for table_row in table_rows:
                table_name = table_row['table_name']
                table_info = await self._discover_table_info(conn, table_name)
                tables[table_name] = table_info

            return DatabaseSchema(
                tenant_id=tenant_id,
                connection_id=connection_id,
                database_name=database_name,
                tables=tables,
                discovered_at=datetime.utcnow()
            )

    async def _discover_table_info(
        self,
        conn: asyncpg.Connection,
        table_name: str
    ) -> TableInfo:
        """Discover detailed information about a table"""

        # Get column information
        columns_query = """
            SELECT column_name,
                   data_type,
                   is_nullable,
                   column_default,
                   character_maximum_length,
                   numeric_precision,
                   numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
        """
        column_rows = await conn.fetch(columns_query, table_name)

        # Get primary key information
        pk_query = """
            SELECT column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                 ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = $1
        """
        pk_columns = {row['column_name'] for row in await conn.fetch(pk_query, table_name)}

        # Get foreign key information
        fk_query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                 ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                 ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = $1
        """
        fk_rows = await conn.fetch(fk_query, table_name)

        # Build column information
        columns = []
        for col_row in column_rows:
            column_name = col_row['column_name']
            is_primary = column_name in pk_columns

            # Find foreign key info
            fk_info = next(
                (row for row in fk_rows if row['column_name'] == column_name),
                None
            )

            column_info = ColumnInfo(
                name=column_name,
                data_type=self._normalize_data_type(col_row),
                is_nullable=col_row['is_nullable'] == 'YES',
                default_value=col_row['column_default'],
                is_primary_key=is_primary,
                is_foreign_key=fk_info is not None,
                foreign_table=fk_info['foreign_table_name'] if fk_info else None,
                foreign_column=fk_info['foreign_column_name'] if fk_info else None
            )
            columns.append(column_info)

        # Get sample data
        sample_data = await self._get_sample_data(conn, table_name, columns[:5])  # Limit to first 5 columns

        # Get table relationships
        relationships = await self._discover_table_relationships(conn, table_name)

        # Get row count estimate
        row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
            sample_data=sample_data,
            relationships=relationships
        )

    async def _get_sample_data(
        self,
        conn: asyncpg.Connection,
        table_name: str,
        columns: List[ColumnInfo]
    ) -> List[Dict[str, Any]]:
        """Get sample data from table"""
        try:
            if not columns:
                return []

            column_names = [col.name for col in columns]
            query = f"""
                SELECT {', '.join(column_names)}
                FROM {table_name}
                ORDER BY random()
                LIMIT 3
            """
            rows = await conn.fetch(query)

            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_name}: {str(e)}")
            return []

    async def _discover_table_relationships(
        self,
        conn: asyncpg.Connection,
        table_name: str
    ) -> List[Dict[str, str]]:
        """Discover table relationships"""
        relationships = []

        # Foreign key relationships (outgoing)
        fk_query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                 ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                 ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = $1
        """
        fk_rows = await conn.fetch(fk_query, table_name)

        for row in fk_rows:
            relationships.append({
                "type": "foreign_key",
                "column": row['column_name'],
                "foreign_table": row['foreign_table_name'],
                "foreign_column": row['foreign_column_name'],
                "constraint_name": row['constraint_name']
            })

        # Referenced by relationships (incoming)
        ref_query = """
            SELECT
                tc.table_name AS referencing_table,
                kcu.column_name AS referencing_column,
                ccu.column_name AS referenced_column,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                 ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                 ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND ccu.table_name = $1
        """
        ref_rows = await conn.fetch(ref_query, table_name)

        for row in ref_rows:
            relationships.append({
                "type": "referenced_by",
                "referencing_table": row['referencing_table'],
                "referencing_column": row['referencing_column'],
                "referenced_column": row['referenced_column'],
                "constraint_name": row['constraint_name']
            })

        return relationships

    def _normalize_data_type(self, column_row: Dict[str, Any]) -> str:
        """Normalize PostgreSQL data type to standard type"""
        data_type = column_row['data_type']

        # Handle character types with length
        if data_type == 'character varying' and column_row['character_maximum_length']:
            return f"VARCHAR({column_row['character_maximum_length']})"
        elif data_type == 'character' and column_row['character_maximum_length']:
            return f"CHAR({column_row['character_maximum_length']})"

        # Handle numeric types with precision
        if data_type == 'numeric':
            if column_row['numeric_precision'] and column_row['numeric_scale']:
                return f"NUMERIC({column_row['numeric_precision']}, {column_row['numeric_scale']})"
            elif column_row['numeric_precision']:
                return f"NUMERIC({column_row['numeric_precision']})"
            else:
                return "NUMERIC"

        # Map common types
        type_mapping = {
            'integer': 'INTEGER',
            'bigint': 'BIGINT',
            'smallint': 'SMALLINT',
            'real': 'REAL',
            'double precision': 'DOUBLE PRECISION',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'timestamp without time zone': 'TIMESTAMP',
            'timestamp with time zone': 'TIMESTAMPTZ',
            'text': 'TEXT',
            'json': 'JSON',
            'jsonb': 'JSONB',
            'uuid': 'UUID',
            'bytea': 'BYTEA'
        }

        return type_mapping.get(data_type, data_type.upper())

    def _decrypt_connection_string(self, encrypted_string: str) -> str:
        """Decrypt database connection string"""
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_string.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt connection string: {str(e)}")
            raise ValueError("Invalid connection string")

    async def invalidate_schema_cache(self, tenant_id: str, connection_id: int):
        """Invalidate schema cache for specific tenant/connection"""
        cache_key = f"{tenant_id}:{connection_id}"
        if cache_key in self.schema_cache:
            del self.schema_cache[cache_key]
            logger.info(f"Invalidated schema cache for {cache_key}")

    async def get_cached_schema(self, tenant_id: str, connection_id: int) -> Optional[DatabaseSchema]:
        """Get cached schema if available and not expired"""
        cache_key = f"{tenant_id}:{connection_id}"

        if cache_key in self.schema_cache:
            cached_schema = self.schema_cache[cache_key]
            if datetime.utcnow() - cached_schema.discovered_at < self.cache_ttl:
                return cached_schema

        return None

    async def close_connection_pools(self):
        """Close all connection pools"""
        for pool in self.connection_pools.values():
            await pool.close()
        self.connection_pools.clear()

    async def check_schema_changes(
        self,
        tenant_id: str,
        connection_id: int,
        connection_string: str
    ) -> bool:
        """
        Check if database schema has changed since last discovery

        Args:
            tenant_id: Tenant ID
            connection_id: Data source connection ID
            connection_string: Encrypted database connection string

        Returns:
            bool: True if schema has changed
        """
        try:
            # Get current cached schema
            cached_schema = await self.get_cached_schema(tenant_id, connection_id)
            if not cached_schema:
                return True  # No cached schema, treat as changed

            # Discover fresh schema
            fresh_schema = await self.discover_tenant_schema(
                tenant_id, connection_id, connection_string, force_refresh=True
            )

            # Compare schemas
            if len(cached_schema.tables) != len(fresh_schema.tables):
                return True

            for table_name, cached_table in cached_schema.tables.items():
                if table_name not in fresh_schema.tables:
                    return True

                fresh_table = fresh_schema.tables[table_name]

                # Compare column counts
                if len(cached_table.columns) != len(fresh_table.columns):
                    return True

                # Compare column structures
                for cached_col in cached_table.columns:
                    fresh_col = next(
                        (c for c in fresh_table.columns if c.name == cached_col.name),
                        None
                    )
                    if not fresh_col or fresh_col.data_type != cached_col.data_type:
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking schema changes: {str(e)}")
            return True  # Assume schema changed on error