"""
数据库适配器接口
支持多种数据库类型的统一接口，为RAG-SQL服务提供数据库抽象层
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """支持的数据库类型"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


@dataclass
class ColumnInfo:
    """数据库列信息"""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None


@dataclass
class TableInfo:
    """数据库表信息"""
    name: str
    table_type: str  # table, view, etc.
    row_count: Optional[int]
    columns: List[ColumnInfo]
    description: Optional[str] = None


@dataclass
class SchemaInfo:
    """数据库schema信息"""
    database_name: str
    database_type: DatabaseType
    tables: Dict[str, TableInfo]
    relationships: List[Dict[str, Any]]
    version: Optional[str] = None
    last_updated: Optional[datetime] = None


@dataclass
class QueryResult:
    """查询结果"""
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time: float
    affected_rows: Optional[int] = None
    has_more: bool = False


@dataclass
class QueryPlan:
    """查询执行计划"""
    plan_id: str
    query: str
    execution_plan: Dict[str, Any]
    estimated_cost: Optional[float] = None
    estimated_rows: Optional[int] = None


class DatabaseInterface(ABC):
    """数据库接口抽象基类"""

    def __init__(self, connection_string: str, **kwargs):
        self.connection_string = connection_string
        self.kwargs = kwargs
        self._connection = None

    @abstractmethod
    async def connect(self) -> bool:
        """建立数据库连接"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开数据库连接"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试数据库连接"""
        pass

    @abstractmethod
    async def get_schema_info(self) -> SchemaInfo:
        """获取数据库schema信息"""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行SQL查询"""
        pass

    @abstractmethod
    async def explain_query(self, query: str) -> QueryPlan:
        """获取查询执行计划"""
        pass

    @abstractmethod
    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证SQL查询语法"""
        pass

    @abstractmethod
    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        pass

    @abstractmethod
    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取表样本数据"""
        pass

    @abstractmethod
    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取表统计信息"""
        pass


class PostgreSQLAdapter(DatabaseInterface):
    """PostgreSQL数据库适配器"""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(connection_string, **kwargs)
        self.pool_size = kwargs.get("pool_size", 10)
        self.max_overflow = kwargs.get("max_overflow", 20)

    async def connect(self) -> bool:
        """建立PostgreSQL连接"""
        try:
            import asyncpg

            self._connection = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=self.pool_size,
                max_overflow=self.max_overflow
            )

            logger.info("PostgreSQL连接建立成功")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            return False

    async def disconnect(self):
        """断开PostgreSQL连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("PostgreSQL连接已断开")

    async def test_connection(self) -> bool:
        """测试PostgreSQL连接"""
        try:
            if not self._connection:
                return await self.connect()

            async with self._connection.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL连接测试失败: {e}")
            return False

    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        return DatabaseType.POSTGRESQL

    async def get_schema_info(self) -> SchemaInfo:
        """获取PostgreSQL schema信息"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                # 获取数据库基本信息
                db_info = await conn.fetchrow("""
                    SELECT current_database() as database_name,
                           version() as version
                """)

                # 获取所有表和视图
                tables_query = """
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY table_name
                """
                tables = await conn.fetch(tables_query)

                # 构建表信息
                table_infos = {}
                for table_record in tables:
                    table_name = table_record["table_name"]
                    table_type = table_record["table_type"]

                    # 获取列信息
                    columns_query = """
                        SELECT column_name, data_type, is_nullable,
                               column_default, character_maximum_length,
                               numeric_precision, numeric_scale
                        FROM information_schema.columns
                        WHERE table_name = $1
                        ORDER BY ordinal_position
                    """
                    columns = await conn.fetch(columns_query, table_name)

                    # 获取主键信息
                    pk_query = """
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                             ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_name = $1
                              AND tc.constraint_type = 'PRIMARY KEY'
                    """
                    pk_columns = [row["column_name"] for row in await conn.fetch(pk_query, table_name)]

                    # 获取外键信息
                    fk_query = """
                        SELECT kcu.column_name,
                               ccu.table_name AS foreign_table_name,
                               ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                             ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage ccu
                             ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.table_name = $1
                              AND tc.constraint_type = 'FOREIGN KEY'
                    """
                    fk_info = await conn.fetch(fk_query, table_name)
                    fk_columns = {row["column_name"]: {
                        "foreign_table": row["foreign_table_name"],
                        "foreign_column": row["foreign_column_name"]
                    } for row in fk_info}

                    # 获取表行数
                    row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

                    # 构建列信息对象
                    column_infos = []
                    for col in columns:
                        is_pk = col["column_name"] in pk_columns
                        fk_info_for_col = fk_columns.get(col["column_name"])
                        is_fk = fk_info_for_col is not None

                        column_infos.append(ColumnInfo(
                            name=col["column_name"],
                            data_type=col["data_type"],
                            is_nullable=col["is_nullable"] == "YES",
                            default_value=col["column_default"],
                            is_primary_key=is_pk,
                            is_foreign_key=is_fk,
                            foreign_table=fk_info_for_col["foreign_table"] if is_fk else None,
                            foreign_column=fk_info_for_col["foreign_column"] if is_fk else None,
                            max_length=col["character_maximum_length"],
                            precision=col["numeric_precision"],
                            scale=col["numeric_scale"]
                        ))

                    table_infos[table_name] = TableInfo(
                        name=table_name,
                        table_type=table_type,
                        row_count=row_count,
                        columns=column_infos
                    )

                # 获取关系信息
                relationships = []
                for fk_query_result in fk_info:
                    relationships.append({
                        "from_table": table_name,
                        "from_column": fk_query_result["column_name"],
                        "to_table": fk_query_result["foreign_table_name"],
                        "to_column": fk_query_result["foreign_column_name"],
                        "relationship_type": "foreign_key"
                    })

                return SchemaInfo(
                    database_name=db_info["database_name"],
                    database_type=self.get_database_type(),
                    tables=table_infos,
                    relationships=relationships,
                    version=db_info["version"],
                    last_updated=datetime.now()
                )

        except Exception as e:
            logger.error(f"获取PostgreSQL schema信息失败: {e}")
            raise

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行PostgreSQL查询"""
        try:
            import time
            start_time = time.time()

            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                if params:
                    result = await conn.fetch(query, *params.values())
                else:
                    result = await conn.fetch(query)

                execution_time = time.time() - start_time

                if not result:
                    return QueryResult(
                        data=[],
                        columns=[],
                        row_count=0,
                        execution_time=execution_time
                    )

                # 转换为字典列表
                columns = [key for key in result[0].keys()]
                data = [dict(row) for row in result]

                return QueryResult(
                    data=data,
                    columns=columns,
                    row_count=len(data),
                    execution_time=execution_time
                )

        except Exception as e:
            logger.error(f"PostgreSQL查询执行失败: {e}")
            raise

    async def explain_query(self, query: str) -> QueryPlan:
        """获取PostgreSQL查询执行计划"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                # 使用EXPLAIN ANALYZE获取详细执行计划
                explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query}"
                result = await conn.fetchrow(explain_query)

                plan_data = result[0] if result else {}

                # 获取预估成本
                estimated_cost = None
                estimated_rows = None

                if isinstance(plan_data, list) and plan_data:
                    plan = plan_data[0]
                    estimated_cost = plan.get("Total Cost")
                    estimated_rows = plan.get("Plan", {}).get("Plan Rows")

                return QueryPlan(
                    plan_id=f"pg_plan_{int(datetime.now().timestamp())}",
                    query=query,
                    execution_plan=plan_data,
                    estimated_cost=estimated_cost,
                    estimated_rows=estimated_rows
                )

        except Exception as e:
            logger.error(f"PostgreSQL执行计划获取失败: {e}")
            raise

    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证PostgreSQL查询语法"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                # 使用EXPLAIN来验证语法，不实际执行
                validate_query = f"EXPLAIN {query}"
                await conn.fetch(validate_query)

            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"PostgreSQL查询验证失败: {error_msg}")
            return False, error_msg

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取PostgreSQL表样本数据"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                query = f"SELECT * FROM {table_name} LIMIT $1"
                result = await conn.fetch(query, limit)

                return [dict(row) for row in result]

        except Exception as e:
            logger.error(f"获取PostgreSQL表样本失败: {e}")
            return []

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取PostgreSQL表统计信息"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            async with self._connection.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats
                    WHERE tablename = $1
                    LIMIT 10
                """, table_name)

                size_info = await conn.fetchrow("""
                    SELECT
                        pg_size_pretty(pg_total_relation_size($1)) as total_size,
                        pg_size_pretty(pg_relation_size($1)) as table_size,
                        pg_size_pretty(pg_total_relation_size($1) - pg_relation_size($1)) as index_size
                """, table_name)

                return {
                    "table_name": table_name,
                    "column_stats": [dict(row) for row in [stats]] if stats else [],
                    "size_info": dict(size_info) if size_info else {}
                }

        except Exception as e:
            logger.error(f"获取PostgreSQL表统计失败: {e}")
            return {}


class MySQLAdapter(DatabaseInterface):
    """MySQL数据库适配器（框架实现）"""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(connection_string, **kwargs)

    async def connect(self) -> bool:
        """建立MySQL连接（待实现）"""
        logger.warning("MySQL适配器待实现")
        return False

    async def disconnect(self):
        """断开MySQL连接（待实现）"""
        logger.warning("MySQL适配器待实现")

    async def test_connection(self) -> bool:
        """测试MySQL连接（待实现）"""
        logger.warning("MySQL适配器待实现")
        return False

    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        return DatabaseType.MYSQL

    async def get_schema_info(self) -> SchemaInfo:
        """获取MySQL schema信息（待实现）"""
        logger.warning("MySQL适配器待实现")
        raise NotImplementedError("MySQL适配器待实现")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行MySQL查询（待实现）"""
        logger.warning("MySQL适配器待实现")
        raise NotImplementedError("MySQL适配器待实现")

    async def explain_query(self, query: str) -> QueryPlan:
        """获取MySQL查询执行计划（待实现）"""
        logger.warning("MySQL适配器待实现")
        raise NotImplementedError("MySQL适配器待实现")

    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证MySQL查询语法（待实现）"""
        logger.warning("MySQL适配器待实现")
        return False, "MySQL适配器待实现"

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取MySQL表样本数据（待实现）"""
        logger.warning("MySQL适配器待实现")
        return []

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取MySQL表统计信息（待实现）"""
        logger.warning("MySQL适配器待实现")
        return {}


class SQLiteDatabaseAdapter(DatabaseInterface):
    """SQLite数据库适配器（框架实现）"""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(connection_string, **kwargs)

    async def connect(self) -> bool:
        """建立SQLite连接（待实现）"""
        logger.warning("SQLite适配器待实现")
        return False

    async def disconnect(self):
        """断开SQLite连接（待实现）"""
        logger.warning("SQLite适配器待实现")

    async def test_connection(self) -> bool:
        """测试SQLite连接（待实现）"""
        logger.warning("SQLite适配器待实现")
        return False

    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        return DatabaseType.SQLITE

    async def get_schema_info(self) -> SchemaInfo:
        """获取SQLite schema信息（待实现）"""
        logger.warning("SQLite适配器待实现")
        raise NotImplementedError("SQLite适配器待实现")

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行SQLite查询（待实现）"""
        logger.warning("SQLite适配器待实现")
        raise NotImplementedError("SQLite适配器待实现")

    async def explain_query(self, query: str) -> QueryPlan:
        """获取SQLite查询执行计划（待实现）"""
        logger.warning("SQLite适配器待实现")
        raise NotImplementedError("SQLite适配器待实现")

    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证SQLite查询语法（待实现）"""
        logger.warning("SQLite适配器待实现")
        return False, "SQLite适配器待实现"

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取SQLite表样本数据（待实现）"""
        logger.warning("SQLite适配器待实现")
        return []

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取SQLite表统计信息（待实现）"""
        logger.warning("SQLite适配器待实现")
        return {}