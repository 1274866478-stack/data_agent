"""
# [DATABASE_INTERFACE] 数据库适配器接口

## [HEADER]
**文件名**: database_interface.py
**职责**: 支持多种数据库类型的统一接口，为RAG-SQL服务提供数据库抽象层
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 数据库适配器接口

## [INPUT]
- **connection_string: str** - 数据库连接字符串
- **kwargs: Dict[str, Any]** - 额外连接参数
- **query: str** - SQL查询语句
- **params: Optional[Dict[str, Any]]** - 查询参数
- **timeout: int** - 查询超时时间（秒）
- **table_name: str** - 表名
- **limit: int** - 限制数量

## [OUTPUT]
- **bool**: 连接/测试连接成功
- **SchemaInfo**: 数据库schema信息
  - database_name: 数据库名称
  - database_type: DatabaseType枚举
  - tables: 字典（表名→TableInfo）
  - relationships: 关系列表
  - version: 数据库版本
  - last_updated: 最后更新时间
- **QueryResult**: 查询结果
  - data: 数据列表（字典列表）
  - columns: 列名列表
  - row_count: 行数
  - execution_time: 执行时间（秒）
  - affected_rows: 影响行数
  - has_more: 是否有更多数据
- **QueryPlan**: 查询执行计划
  - plan_id: 计划ID
  - query: 查询语句
  - execution_plan: 执行计划（JSON格式）
  - estimated_cost: 预估成本
  - estimated_rows: 预估行数
- **Tuple[bool, Optional[str]]**: 验证结果和错误消息
- **List[Dict[str, Any]]**: 表样本数据
- **Dict[str, Any]**: 表统计信息

**上游依赖** (已读取源码):
- 无（独立数据库适配器）

**下游依赖** (需要反向索引分析):
- [database_factory.py](./database_factory.py) - 数据库工厂使用适配器
- [llm_service.py](./llm_service.py) - LLM服务执行SQL查询
- [query_optimization_service.py](./query_optimization_service.py) - 查询优化服务获取schema

**调用方**:
- 数据库工厂创建适配器实例
- LLM服务执行SQL查询和获取schema
- 查询优化服务分析查询计划
- 数据源服务测试连接

## [STATE]
- **数据库类型**: DatabaseType枚举（POSTGRESQL, MYSQL, SQLITE, SQLSERVER, ORACLE）
- **数据类**: ColumnInfo, TableInfo, SchemaInfo, QueryResult, QueryPlan
- **抽象基类**: DatabaseInterface（ABC）
  - connect/disconnect/test_connection: 连接管理
  - get_schema_info: 获取schema信息
  - execute_query: 执行SQL查询
  - explain_query: 获取执行计划
  - validate_query: 验证SQL语法
  - get_database_type: 获取数据库类型
  - get_table_sample: 获取表样本
  - get_table_statistics: 获取表统计
- **PostgreSQL适配器**: PostgreSQLAdapter
  - asyncpg连接池（min_size=1, max_size=10）
  - 支持参数化查询（$1, $2...）
  - EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS)
  - information_schema查询表/列/主键/外键
- **MySQL适配器**: MySQLAdapter
  - aiomysql连接池（minsize=1, maxsize=10）
  - 支持参数化查询（%s占位符）
  - EXPLAIN FORMAT=JSON
  - information_schema查询
- **SQLite适配器**: SQLiteDatabaseAdapter
  - aiosqlite连接（支持:memory:）
  - 支持参数化查询（?占位符）
  - EXPLAIN QUERY PLAN
  - PRAGMA table_info/foreign_key_list/index_list
  - sqlite_master查询
- **连接池管理**: 连接复用和自动释放
- **异步上下文管理器**: async with conn/acquire()自动释放连接
- **错误处理**: 所有方法捕获异常并记录日志

## [SIDE-EFFECTS]
- **异步连接池**:
  - asyncpg.create_pool创建PostgreSQL连接池
  - aiomysql.create_pool创建MySQL连接池
  - aiosqlite.connect创建SQLite连接
- **连接获取/释放**:
  - async with self._connection.acquire() as conn（PostgreSQL）
  - async with self._pool.acquire() as conn（MySQL）
  - 直接使用self._connection（SQLite单连接）
- **游标操作**:
  - async with conn.cursor(aiomysql.DictCursor) as cursor（MySQL）
  - await cursor.execute/query/fetchone/fetchall
- **参数化查询**:
  - PostgreSQL: await conn.fetch(query, *params.values())（$1, $2占位符）
  - MySQL: await cursor.execute(query, tuple(params.values()))（%s占位符）
  - SQLite: await self._connection.execute(query, param_values)（?占位符）
- **字典转换**: [dict(row) for row in result]转换Record为字典
- **时间测量**: time.time()计算执行时间
- **列名提取**: [key for key in result[0].keys()]提取列名
- **条件过滤**: WHERE table_schema NOT IN ('information_schema', 'pg_catalog')过滤系统表
- **字符串解析**: urllib.parse.urlparse解析MySQL连接字符串
- **字典构建**: {**default_config, **model_config}合并配置
- **列表推导式**: [row["column_name"] for row in await conn.fetch(pk_query)]提取主键列
- **外键映射**: {row["column_name"]: {...} for row in fk_info}构建外键字典
- **PRAGMA查询**:
  - PRAGMA table_info('{table_name}')获取列信息
  - PRAGMA foreign_key_list('{table_name}')获取外键
  - PRAGMA index_list('{table_name}')获取索引
- **数据类型映射**:
  - PostgreSQL: information_schema.columns.data_type
  - MySQL: information_schema.columns.data_type
  - SQLite: PRAGMA table_info的type字段
- **主键/外键检测**:
  - PostgreSQL: information_schema.table_constraints
  - MySQL: column_key == "PRI"/referenced_table_name IS NOT NULL
  - SQLite: PRAGMA的pk字段（1=主键）/foreign_key_list
- **行数统计**: SELECT COUNT(*) FROM {table_name}
- **统计信息**:
  - PostgreSQL: pg_stats, pg_size_pretty
  - MySQL: information_schema.tables, information_schema.statistics
  - SQLite: PRAGMA index_info, dbstat虚拟表
- **字节格式化**: _format_bytes转换字节为可读单位（B/KB/MB/GB/TB/PB）
- **路径解析**: _parse_connection_string解析sqlite:///路径
- **外键启用**: PRAGMA foreign_keys = ON（SQLite）
- **行工厂设置**: row_factory = aiosqlite.Row（SQLite返回字典）
- **异常处理**: try-except捕获所有异常，logger.error记录错误，重新抛出
- **日志记录**: logger.info记录连接成功，logger.error记录失败

## [POS]
**路径**: backend/src/app/services/database_interface.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 无外部依赖（数据库驱动按需导入）
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
                max_size=self.pool_size
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
    """MySQL数据库适配器"""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(connection_string, **kwargs)
        self.pool_size = kwargs.get("pool_size", 10)
        self._pool = None

    async def connect(self) -> bool:
        """建立MySQL连接池"""
        try:
            import aiomysql
            import urllib.parse

            # 解析连接字符串
            parsed = urllib.parse.urlparse(self.connection_string)
            db_config = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 3306,
                'user': parsed.username,
                'password': parsed.password or '',
                'db': parsed.path.lstrip('/'),
                'autocommit': True,
                'charset': 'utf8mb4',
                'minsize': 1,
                'maxsize': self.pool_size
            }

            self._pool = await aiomysql.create_pool(**db_config)
            logger.info("MySQL连接池建立成功")
            return True

        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False

    async def disconnect(self):
        """断开MySQL连接"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("MySQL连接已断开")

    async def test_connection(self) -> bool:
        """测试MySQL连接"""
        try:
            if not self._pool:
                return await self.connect()

            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()
            return True

        except Exception as e:
            logger.error(f"MySQL连接测试失败: {e}")
            return False

    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        return DatabaseType.MYSQL

    async def get_schema_info(self) -> SchemaInfo:
        """获取MySQL schema信息"""
        try:
            import aiomysql

            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 获取数据库基本信息
                    await cursor.execute("SELECT DATABASE() as database_name, VERSION() as version")
                    db_info = await cursor.fetchone()

                    # 获取所有表
                    await cursor.execute("""
                        SELECT table_name, table_type
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE()
                        ORDER BY table_name
                    """)
                    tables = await cursor.fetchall()

                    # 构建表信息
                    table_infos = {}
                    all_relationships = []

                    for table_record in tables:
                        table_name = table_record["table_name"]
                        table_type = table_record["table_type"]

                        # 获取列信息
                        await cursor.execute("""
                            SELECT column_name, data_type, is_nullable,
                                   column_default, character_maximum_length,
                                   numeric_precision, numeric_scale, column_key
                            FROM information_schema.columns
                            WHERE table_schema = DATABASE() AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table_name,))
                        columns = await cursor.fetchall()

                        # 获取主键列
                        pk_columns = [col["column_name"] for col in columns if col["column_key"] == "PRI"]

                        # 获取外键信息
                        await cursor.execute("""
                            SELECT column_name,
                                   referenced_table_name,
                                   referenced_column_name
                            FROM information_schema.key_column_usage
                            WHERE table_schema = DATABASE()
                              AND table_name = %s
                              AND referenced_table_name IS NOT NULL
                        """, (table_name,))
                        fk_info = await cursor.fetchall()
                        fk_columns = {row["column_name"]: {
                            "foreign_table": row["referenced_table_name"],
                            "foreign_column": row["referenced_column_name"]
                        } for row in fk_info}

                        # 获取表行数
                        await cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table_name}`")
                        row_count_result = await cursor.fetchone()
                        row_count = row_count_result["cnt"] if row_count_result else 0

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

                        # 收集关系信息
                        for fk_row in fk_info:
                            all_relationships.append({
                                "from_table": table_name,
                                "from_column": fk_row["column_name"],
                                "to_table": fk_row["referenced_table_name"],
                                "to_column": fk_row["referenced_column_name"],
                                "relationship_type": "foreign_key"
                            })

                    return SchemaInfo(
                        database_name=db_info["database_name"],
                        database_type=self.get_database_type(),
                        tables=table_infos,
                        relationships=all_relationships,
                        version=db_info["version"],
                        last_updated=datetime.now()
                    )

        except Exception as e:
            logger.error(f"获取MySQL schema信息失败: {e}")
            raise

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行MySQL查询"""
        try:
            import time
            import aiomysql

            start_time = time.time()

            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if params:
                        await cursor.execute(query, tuple(params.values()))
                    else:
                        await cursor.execute(query)

                    execution_time = time.time() - start_time

                    # 检查是否是SELECT等返回数据的查询
                    if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                        result = await cursor.fetchall()

                        if not result:
                            return QueryResult(
                                data=[],
                                columns=[],
                                row_count=0,
                                execution_time=execution_time
                            )

                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        data = [dict(row) for row in result]

                        return QueryResult(
                            data=data,
                            columns=columns,
                            row_count=len(data),
                            execution_time=execution_time
                        )
                    else:
                        return QueryResult(
                            data=[],
                            columns=[],
                            row_count=0,
                            execution_time=execution_time,
                            affected_rows=cursor.rowcount
                        )

        except Exception as e:
            logger.error(f"MySQL查询执行失败: {e}")
            raise

    async def explain_query(self, query: str) -> QueryPlan:
        """获取MySQL查询执行计划"""
        try:
            import aiomysql

            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 使用EXPLAIN获取执行计划
                    explain_query = f"EXPLAIN FORMAT=JSON {query}"
                    await cursor.execute(explain_query)
                    result = await cursor.fetchone()

                    plan_data = {}
                    estimated_cost = None
                    estimated_rows = None

                    if result and 'EXPLAIN' in result:
                        import json
                        plan_data = json.loads(result['EXPLAIN'])
                        # 从JSON执行计划中提取成本和行数
                        if 'query_block' in plan_data:
                            query_block = plan_data['query_block']
                            if 'cost_info' in query_block:
                                estimated_cost = float(query_block['cost_info'].get('query_cost', 0))
                            if 'table' in query_block:
                                estimated_rows = query_block['table'].get('rows_examined_per_scan')

                    return QueryPlan(
                        plan_id=f"mysql_plan_{int(datetime.now().timestamp())}",
                        query=query,
                        execution_plan=plan_data,
                        estimated_cost=estimated_cost,
                        estimated_rows=estimated_rows
                    )

        except Exception as e:
            logger.error(f"MySQL执行计划获取失败: {e}")
            raise

    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证MySQL查询语法"""
        try:
            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 使用EXPLAIN来验证语法
                    validate_query = f"EXPLAIN {query}"
                    await cursor.execute(validate_query)

            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"MySQL查询验证失败: {error_msg}")
            return False, error_msg

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取MySQL表样本数据"""
        try:
            import aiomysql

            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    query = f"SELECT * FROM `{table_name}` LIMIT %s"
                    await cursor.execute(query, (limit,))
                    result = await cursor.fetchall()

                    return [dict(row) for row in result]

        except Exception as e:
            logger.error(f"获取MySQL表样本失败: {e}")
            return []

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取MySQL表统计信息"""
        try:
            import aiomysql

            if not self._pool:
                raise Exception("数据库未连接")

            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 获取表基本统计信息
                    await cursor.execute("""
                        SELECT
                            table_name,
                            table_rows,
                            data_length,
                            index_length,
                            avg_row_length,
                            auto_increment,
                            create_time,
                            update_time
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE() AND table_name = %s
                    """, (table_name,))
                    stats = await cursor.fetchone()

                    # 获取列的索引信息
                    await cursor.execute("""
                        SELECT
                            column_name,
                            index_name,
                            seq_in_index,
                            cardinality
                        FROM information_schema.statistics
                        WHERE table_schema = DATABASE() AND table_name = %s
                    """, (table_name,))
                    index_stats = await cursor.fetchall()

                    return {
                        "table_name": table_name,
                        "table_stats": dict(stats) if stats else {},
                        "size_info": {
                            "data_size": self._format_bytes(stats["data_length"]) if stats else "0 B",
                            "index_size": self._format_bytes(stats["index_length"]) if stats else "0 B",
                            "total_size": self._format_bytes(
                                (stats["data_length"] or 0) + (stats["index_length"] or 0)
                            ) if stats else "0 B"
                        },
                        "index_stats": [dict(row) for row in index_stats]
                    }

        except Exception as e:
            logger.error(f"获取MySQL表统计失败: {e}")
            return {}

    def _format_bytes(self, size: int) -> str:
        """格式化字节大小"""
        if size is None:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size) < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class SQLiteDatabaseAdapter(DatabaseInterface):
    """SQLite数据库适配器 - 完整实现"""

    def __init__(self, connection_string: str, **kwargs):
        super().__init__(connection_string, **kwargs)
        # 解析SQLite连接字符串，提取数据库文件路径
        # 支持格式: sqlite:///path/to/db.sqlite 或 sqlite:///:memory:
        self._db_path = self._parse_connection_string(connection_string)

    def _parse_connection_string(self, connection_string: str) -> str:
        """解析SQLite连接字符串，提取数据库文件路径"""
        if connection_string.startswith("sqlite:///"):
            return connection_string[10:]  # 移除 "sqlite:///"
        elif connection_string.startswith("sqlite://"):
            path = connection_string[9:]
            return path if path else ":memory:"
        else:
            # 假设是直接的文件路径
            return connection_string

    async def connect(self) -> bool:
        """建立SQLite连接"""
        try:
            import aiosqlite

            self._connection = await aiosqlite.connect(self._db_path)
            # 启用外键约束
            await self._connection.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂以返回字典
            self._connection.row_factory = aiosqlite.Row

            logger.info(f"SQLite连接建立成功: {self._db_path}")
            return True

        except Exception as e:
            logger.error(f"SQLite连接失败: {e}")
            return False

    async def disconnect(self):
        """断开SQLite连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("SQLite连接已断开")

    async def test_connection(self) -> bool:
        """测试SQLite连接"""
        try:
            if not self._connection:
                return await self.connect()

            cursor = await self._connection.execute("SELECT 1")
            await cursor.fetchone()
            await cursor.close()
            return True

        except Exception as e:
            logger.error(f"SQLite连接测试失败: {e}")
            return False

    def get_database_type(self) -> DatabaseType:
        """获取数据库类型"""
        return DatabaseType.SQLITE

    async def get_schema_info(self) -> SchemaInfo:
        """获取SQLite schema信息"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            # 获取SQLite版本
            cursor = await self._connection.execute("SELECT sqlite_version()")
            version_row = await cursor.fetchone()
            version = version_row[0] if version_row else "unknown"
            await cursor.close()

            # 获取所有表和视图
            tables_query = """
                SELECT name, type
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
            cursor = await self._connection.execute(tables_query)
            tables = await cursor.fetchall()
            await cursor.close()

            table_infos = {}
            all_relationships = []

            for table_record in tables:
                table_name = table_record[0]
                table_type = table_record[1]

                # 获取列信息 (使用 PRAGMA table_info)
                pragma_query = f"PRAGMA table_info('{table_name}')"
                cursor = await self._connection.execute(pragma_query)
                columns_data = await cursor.fetchall()
                await cursor.close()

                # 获取外键信息 (使用 PRAGMA foreign_key_list)
                fk_query = f"PRAGMA foreign_key_list('{table_name}')"
                cursor = await self._connection.execute(fk_query)
                fk_data = await cursor.fetchall()
                await cursor.close()

                # 构建外键映射
                fk_columns = {}
                for fk in fk_data:
                    # fk: (id, seq, table, from, to, on_update, on_delete, match)
                    from_column = fk[3]
                    to_table = fk[2]
                    to_column = fk[4]
                    fk_columns[from_column] = {
                        "foreign_table": to_table,
                        "foreign_column": to_column
                    }
                    all_relationships.append({
                        "from_table": table_name,
                        "from_column": from_column,
                        "to_table": to_table,
                        "to_column": to_column,
                        "relationship_type": "foreign_key"
                    })

                # 获取表行数
                try:
                    count_cursor = await self._connection.execute(
                        f"SELECT COUNT(*) FROM \"{table_name}\""
                    )
                    row_count_result = await count_cursor.fetchone()
                    row_count = row_count_result[0] if row_count_result else 0
                    await count_cursor.close()
                except Exception:
                    row_count = 0

                # 构建列信息对象
                column_infos = []
                for col in columns_data:
                    # col: (cid, name, type, notnull, dflt_value, pk)
                    col_name = col[1]
                    col_type = col[2]
                    is_nullable = col[3] == 0
                    default_value = col[4]
                    is_pk = col[5] == 1
                    fk_info_for_col = fk_columns.get(col_name)
                    is_fk = fk_info_for_col is not None

                    column_infos.append(ColumnInfo(
                        name=col_name,
                        data_type=col_type,
                        is_nullable=is_nullable,
                        default_value=default_value,
                        is_primary_key=is_pk,
                        is_foreign_key=is_fk,
                        foreign_table=fk_info_for_col["foreign_table"] if is_fk else None,
                        foreign_column=fk_info_for_col["foreign_column"] if is_fk else None
                    ))

                table_infos[table_name] = TableInfo(
                    name=table_name,
                    table_type=table_type,
                    row_count=row_count,
                    columns=column_infos
                )

            # 数据库名称从文件路径中提取
            import os
            db_name = os.path.basename(self._db_path) if self._db_path != ":memory:" else "memory"

            return SchemaInfo(
                database_name=db_name,
                database_type=self.get_database_type(),
                tables=table_infos,
                relationships=all_relationships,
                version=version,
                last_updated=datetime.now()
            )

        except Exception as e:
            logger.error(f"获取SQLite schema信息失败: {e}")
            raise

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> QueryResult:
        """执行SQLite查询"""
        try:
            import time
            start_time = time.time()

            if not self._connection:
                raise Exception("数据库未连接")

            # SQLite使用?作为占位符，需要转换命名参数
            if params:
                # 将命名参数转换为位置参数列表
                param_values = list(params.values())
                cursor = await self._connection.execute(query, param_values)
            else:
                cursor = await self._connection.execute(query)

            execution_time = time.time() - start_time

            # 检查是否是SELECT等返回数据的查询
            query_upper = query.strip().upper()
            if query_upper.startswith(('SELECT', 'PRAGMA')):
                rows = await cursor.fetchall()
                await cursor.close()

                if not rows:
                    return QueryResult(
                        data=[],
                        columns=[],
                        row_count=0,
                        execution_time=execution_time
                    )

                # 获取列名
                columns = [description[0] for description in cursor.description] if cursor.description else []

                # 转换为字典列表
                data = [dict(zip(columns, row)) for row in rows]

                return QueryResult(
                    data=data,
                    columns=columns,
                    row_count=len(data),
                    execution_time=execution_time
                )
            else:
                # INSERT, UPDATE, DELETE等操作
                affected_rows = cursor.rowcount
                await self._connection.commit()
                await cursor.close()

                return QueryResult(
                    data=[],
                    columns=[],
                    row_count=0,
                    execution_time=execution_time,
                    affected_rows=affected_rows
                )

        except Exception as e:
            logger.error(f"SQLite查询执行失败: {e}")
            raise

    async def explain_query(self, query: str) -> QueryPlan:
        """获取SQLite查询执行计划"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            # SQLite使用EXPLAIN QUERY PLAN
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            cursor = await self._connection.execute(explain_query)
            rows = await cursor.fetchall()
            await cursor.close()

            # 解析执行计划
            plan_steps = []
            for row in rows:
                # row: (selectid, order, from, detail)
                plan_steps.append({
                    "select_id": row[0],
                    "order": row[1],
                    "from": row[2],
                    "detail": row[3]
                })

            return QueryPlan(
                plan_id=f"sqlite_plan_{int(datetime.now().timestamp())}",
                query=query,
                execution_plan={"steps": plan_steps},
                estimated_cost=None,  # SQLite不提供成本估算
                estimated_rows=None
            )

        except Exception as e:
            logger.error(f"SQLite执行计划获取失败: {e}")
            raise

    async def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证SQLite查询语法"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            # 使用EXPLAIN来验证语法，不实际执行
            validate_query = f"EXPLAIN {query}"
            cursor = await self._connection.execute(validate_query)
            await cursor.close()

            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"SQLite查询验证失败: {error_msg}")
            return False, error_msg

    async def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取SQLite表样本数据"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            query = f"SELECT * FROM \"{table_name}\" LIMIT ?"
            cursor = await self._connection.execute(query, (limit,))
            rows = await cursor.fetchall()

            # 获取列名
            columns = [description[0] for description in cursor.description] if cursor.description else []
            await cursor.close()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"获取SQLite表样本失败: {e}")
            return []

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取SQLite表统计信息"""
        try:
            if not self._connection:
                raise Exception("数据库未连接")

            # 获取行数
            count_cursor = await self._connection.execute(
                f"SELECT COUNT(*) FROM \"{table_name}\""
            )
            row_count = (await count_cursor.fetchone())[0]
            await count_cursor.close()

            # 获取索引信息
            index_cursor = await self._connection.execute(
                f"PRAGMA index_list('{table_name}')"
            )
            indexes = await index_cursor.fetchall()
            await index_cursor.close()

            index_info = []
            for idx in indexes:
                # idx: (seq, name, unique, origin, partial)
                idx_name = idx[1]
                idx_unique = idx[2] == 1

                # 获取索引列信息
                idx_col_cursor = await self._connection.execute(
                    f"PRAGMA index_info('{idx_name}')"
                )
                idx_columns = await idx_col_cursor.fetchall()
                await idx_col_cursor.close()

                columns = [col[2] for col in idx_columns]  # col[2] is column name

                index_info.append({
                    "name": idx_name,
                    "unique": idx_unique,
                    "columns": columns
                })

            # 获取页面信息（如果可用）
            try:
                # 使用dbstat虚拟表获取大小信息（需要SQLite编译时启用）
                size_cursor = await self._connection.execute("""
                    SELECT
                        SUM(pgsize) as total_size,
                        COUNT(*) as page_count
                    FROM dbstat
                    WHERE name = ?
                """, (table_name,))
                size_info = await size_cursor.fetchone()
                await size_cursor.close()

                total_size = size_info[0] if size_info and size_info[0] else 0
                page_count = size_info[1] if size_info and size_info[1] else 0
            except Exception:
                # dbstat不可用时使用替代方法
                total_size = 0
                page_count = 0

            return {
                "table_name": table_name,
                "row_count": row_count,
                "indexes": index_info,
                "size_info": {
                    "total_size_bytes": total_size,
                    "page_count": page_count,
                    "total_size": self._format_bytes(total_size)
                }
            }

        except Exception as e:
            logger.error(f"获取SQLite表统计失败: {e}")
            return {}

    def _format_bytes(self, size: int) -> str:
        """格式化字节大小"""
        if size is None or size == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size) < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"