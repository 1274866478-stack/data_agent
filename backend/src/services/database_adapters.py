"""
数据库适配器抽象层
支持多种数据库类型的统一接口，为未来扩展做准备
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
from enum import Enum

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """支持的数据库类型"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


class DatabaseFeature(str, Enum):
    """数据库功能特性"""
    SCHEMA_DISCOVERY = "schema_discovery"
    JSON_SUPPORT = "json_support"
    FULL_TEXT_SEARCH = "full_text_search"
    WINDOW_FUNCTIONS = "window_functions"
    CTE_SUPPORT = "cte_support"
    JSON_AGG = "json_agg"
    ARRAY_SUPPORT = "array_support"
    UPSERT = "upsert"


class DatabaseCapability:
    """数据库能力描述"""

    def __init__(self, db_type: DatabaseType):
        self.db_type = db_type
        self.features = set()
        self.version_support = {}
        self.syntax_differences = {}

        # 根据数据库类型初始化能力
        self._initialize_capabilities()

    def _initialize_capabilities(self):
        """根据数据库类型初始化能力"""
        if self.db_type == DatabaseType.POSTGRESQL:
            self.features.update({
                DatabaseFeature.SCHEMA_DISCOVERY,
                DatabaseFeature.JSON_SUPPORT,
                DatabaseFeature.FULL_TEXT_SEARCH,
                DatabaseFeature.WINDOW_FUNCTIONS,
                DatabaseFeature.CTE_SUPPORT,
                DatabaseFeature.JSON_AGG,
                DatabaseFeature.ARRAY_SUPPORT,
                DatabaseFeature.UPSERT
            })

        elif self.db_type == DatabaseType.MYSQL:
            self.features.update({
                DatabaseFeature.SCHEMA_DISCOVERY,
                DatabaseFeature.JSON_SUPPORT,
                DatabaseFeature.FULL_TEXT_SEARCH,
                DatabaseFeature.WINDOW_FUNCTIONS,
                DatabaseFeature.CTE_SUPPORT,
                DatabaseFeature.UPSERT
                # MySQL没有原生ARRAY支持，JSON_AGG需要特殊处理
            })

        elif self.db_type == DatabaseType.SQLITE:
            self.features.update({
                DatabaseFeature.SCHEMA_DISCOVERY,
                DatabaseFeature.JSON_SUPPORT,  # 通过扩展
                DatabaseFeature.FULL_TEXT_SEARCH,  # 通过FTS扩展
                DatabaseFeature.WINDOW_FUNCTIONS,
                DatabaseFeature.CTE_SUPPORT,
                DatabaseFeature.UPSERT
            }

    def supports_feature(self, feature: DatabaseFeature) -> bool:
        """检查是否支持某个功能"""
        return feature in self.features

    def get_dialect(self) -> str:
        """获取数据库方言"""
        dialect_map = {
            DatabaseType.POSTGRESQL: "postgresql",
            DatabaseType.MYSQL: "mysql",
            DatabaseType.SQLITE: "sqlite",
            DatabaseType.SQLSERVER: "mssql",
            DatabaseType.ORACLE: "oracle"
        }
        return dialect_map.get(self.db_type, "postgresql")


class DatabaseAdapter(ABC):
    """数据库适配器抽象基类"""

    def __init__(self, connection_string: str, tenant_id: str):
        self.connection_string = connection_string
        self.tenant_id = tenant_id
        self.db_type = self._detect_database_type()
        self.capability = DatabaseCapability(self.db_type)

    @abstractmethod
    def _detect_database_type(self) -> DatabaseType:
        """检测数据库类型"""
        pass

    @abstractmethod
    async def get_connection(self):
        """获取数据库连接"""
        pass

    @abstractmethod
    async def close_connection(self):
        """关闭数据库连接"""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """执行查询"""
        pass

    @abstractmethod
    async def get_schema_info(self, table_name: str = None) -> Dict[str, Any]:
        """获取数据库结构信息"""
        pass

    @abstractmethod
    async def get_tables(self) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        pass

    @abstractmethod
    async def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        pass

    @abstractmethod
    async def get_foreign_keys(self, table_name: str = None) -> List[Dict[str, Any]]:
        """获取外键信息"""
        pass

    @abstractmethod
    async def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取表的示例数据"""
        pass

    async def validate_query_syntax(self, query: str) -> Dict[str, Any]:
        """验证查询语法"""
        try:
            # 使用EXPLAIN来验证查询语法（不实际执行）
            explain_query = f"EXPLAIN {query}"
            await self.execute_query(explain_query)
            return {"is_valid": True, "message": "语法正确"}
        except Exception as e:
            return {"is_valid": False, "error": str(e)}

    def get_dialect_specific_sql(self, query_type: str, **kwargs) -> str:
        """获取特定数据库方言的SQL"""
        if query_type == "limit":
            limit = kwargs.get("limit", 10)
            offset = kwargs.get("offset", 0)

            if self.db_type == DatabaseType.SQLSERVER:
                return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
            elif self.db_type == DatabaseType.ORACLE:
                return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
            else:
                # PostgreSQL, MySQL, SQLite
                return f"LIMIT {limit} OFFSET {offset}"

        elif query_type == "json_agg":
            column = kwargs.get("column", "*")
            alias = kwargs.get("alias", "json_data")

            if self.db_type == DatabaseType.POSTGRESQL:
                return f"json_agg({column}) as {alias}"
            elif self.db_type == DatabaseType.MYSQL:
                return f"JSON_ARRAYAGG({column}) as {alias}"
            else:
                # SQLite不支持原生JSON聚合，需要使用替代方案
                return f"'[' || GROUP_CONCAT(quote({column})) || ']' as {alias}"

        elif query_type == "upsert":
            table = kwargs.get("table")
            columns = kwargs.get("columns", [])
            values = kwargs.get("values", [])
            conflict_columns = kwargs.get("conflict_columns", [])

            if self.db_type == DatabaseType.POSTGRESQL:
                return f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(['%s'] * len(values))})
                ON CONFLICT ({', '.join(conflict_columns)})
                DO UPDATE SET {', '.join([f"{col} = EXCLUDED.{col}" for col in columns])}
                """
            elif self.db_type == DatabaseType.MYSQL:
                return f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(['%s'] * len(values))})
                ON DUPLICATE KEY UPDATE {', '.join([f"{col} = VALUES({col})" for col in columns])}
                """
            else:
                # SQLite和其他数据库需要使用替代方案
                return None


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL适配器"""

    def _detect_database_type(self) -> DatabaseType:
        """检测为PostgreSQL"""
        return DatabaseType.POSTGRESQL

    async def get_connection(self):
        """获取PostgreSQL连接"""
        import asyncpg

        try:
            connection = await asyncpg.connect(self.connection_string)
            return connection
        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            raise

    async def close_connection(self, connection):
        """关闭PostgreSQL连接"""
        if connection:
            await connection.close()

    async def execute_query(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """执行PostgreSQL查询"""
        connection = None
        try:
            connection = await self.get_connection()

            if params:
                result = await connection.fetch(query, *params.values())
            else:
                result = await connection.fetch(query)

            # 转换结果为字典列表
            data = [dict(row) for row in result]

            # 提取列名
            columns = list(result[0].keys()) if result else []

            return {
                "success": True,
                "data": data,
                "columns": columns,
                "row_count": len(data)
            }

        except Exception as e:
            logger.error(f"PostgreSQL查询执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "columns": [],
                "row_count": 0
            }
        finally:
            await self.close_connection(connection)

    async def get_schema_info(self, table_name: str = None) -> Dict[str, Any]:
        """获取PostgreSQL结构信息"""
        tables_query = """
        SELECT
            table_name,
            table_type,
            table_comment
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """

        if table_name:
            tables_query += f" AND table_name = '{table_name}'"

        tables_query += " ORDER BY table_name"

        tables_result = await self.execute_query(tables_query)

        # 获取列信息
        columns_query = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """

        if table_name:
            columns_query += f" AND table_name = '{table_name}'"

        columns_query += " ORDER BY table_name, ordinal_position"

        columns_result = await self.execute_query(columns_query)

        # 获取外键信息
        fk_query = """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """

        if table_name:
            fk_query += f" AND tc.table_name = '{table_name}'"

        fk_result = await self.execute_query(fk_query)

        return {
            "database_type": "postgresql",
            "tables": tables_result.get("data", []),
            "columns": columns_result.get("data", []),
            "foreign_keys": fk_result.get("data", [])
        }

    async def get_tables(self) -> List[Dict[str, Any]]:
        """获取PostgreSQL所有表信息"""
        query = """
        SELECT
            table_name as name,
            table_type as type,
            COALESCE(table_comment, '') as description
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """

        result = await self.execute_query(query)
        return result.get("data", [])

    async def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取PostgreSQL表的列信息"""
        query = """
        SELECT
            column_name as name,
            data_type as type,
            is_nullable as nullable,
            column_default as default_value,
            character_maximum_length as max_length
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
        """

        result = await self.execute_query(query, {"table_name": table_name})
        return result.get("data", [])

    async def get_foreign_keys(self, table_name: str = None) -> List[Dict[str, Any]]:
        """获取PostgreSQL外键信息"""
        query = """
        SELECT
            tc.table_name as source_table,
            kcu.column_name as source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column,
            tc.constraint_name as constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """

        params = {}
        if table_name:
            query += " AND tc.table_name = %(table_name)s"
            params["table_name"] = table_name

        result = await self.execute_query(query, params)
        return result.get("data", [])

    async def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取PostgreSQL表的示例数据"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        result = await self.execute_query(query)
        return result.get("data", [])


class MySQLAdapter(DatabaseAdapter):
    """MySQL适配器实现"""

    def __init__(self, connection_string: str, tenant_id: str):
        super().__init__(connection_string, tenant_id)
        self.connection = None

    def _detect_database_type(self) -> DatabaseType:
        """检测为MySQL"""
        return DatabaseType.MYSQL

    async def get_connection(self):
        """获取MySQL连接"""
        if self.connection is None:
            try:
                # 尝试导入aiomysql
                import aiomysql
                import urllib.parse

                # 解析连接字符串
                if self.connection_string.startswith("mysql://"):
                    # 转换标准mysql://到aiomysql格式
                    parsed = urllib.parse.urlparse(self.connection_string)
                    db_config = {
                        'host': parsed.hostname or 'localhost',
                        'port': parsed.port or 3306,
                        'user': parsed.username,
                        'password': parsed.password,
                        'db': parsed.path.lstrip('/'),
                        'autocommit': True,
                        'charset': 'utf8mb4'
                    }

                    self.connection = await aiomysql.connect(**db_config)
                    logger.info(f"MySQL连接成功: {db_config['host']}:{db_config['port']}")
                else:
                    raise ValueError(f"不支持的MySQL连接字符串格式: {self.connection_string}")

            except ImportError:
                logger.error("aiomysql库未安装，无法使用MySQL连接")
                raise
            except Exception as e:
                logger.error(f"MySQL连接失败: {e}")
                raise

        return self.connection

    async def close_connection(self):
        """关闭MySQL连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("MySQL连接已关闭")

    async def execute_query(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """执行查询"""
        try:
            conn = await self.get_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)

            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)

            # 获取结果
            if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                rows = await cursor.fetchall()
                result = {
                    'data': rows,
                    'row_count': len(rows),
                    'columns': [desc[0] for desc in cursor.description] if cursor.description else []
                }
            else:
                result = {
                    'data': [],
                    'row_count': cursor.rowcount,
                    'columns': []
                }

            await cursor.close()
            return result

        except Exception as e:
            logger.error(f"MySQL查询执行失败: {e}")
            raise

    async def get_schema_info(self, table_name: str = None) -> Dict[str, Any]:
        """获取数据库结构信息"""
        try:
            schema_info = {
                'database_type': 'mysql',
                'tables': {}
            }

            # 获取表信息
            if table_name:
                tables_info = await self.execute_query(
                    "SELECT table_name, table_comment FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = %s",
                    {'table_name': table_name}
                )
            else:
                tables_info = await self.execute_query(
                    "SELECT table_name, table_comment FROM information_schema.tables "
                    "WHERE table_schema = DATABASE()"
                )

            for table_info in tables_info['data']:
                tbl_name = table_info['table_name']
                schema_info['tables'][tbl_name] = {
                    'name': tbl_name,
                    'description': table_info.get('table_comment', ''),
                    'columns': await self.get_columns(tbl_name),
                    'foreign_keys': await self.get_foreign_keys(tbl_name)
                }

            return schema_info

        except Exception as e:
            logger.error(f"获取MySQL schema信息失败: {e}")
            raise

    async def get_tables(self) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        try:
            result = await self.execute_query(
                "SELECT table_name, table_comment, table_rows "
                "FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                "AND table_type = 'BASE TABLE'"
            )

            tables = []
            for row in result['data']:
                tables.append({
                    'name': row['table_name'],
                    'description': row.get('table_comment', ''),
                    'estimated_rows': row.get('table_rows', 0)
                })

            return tables

        except Exception as e:
            logger.error(f"获取MySQL表信息失败: {e}")
            raise

    async def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            result = await self.execute_query(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    column_comment,
                    column_key,
                    extra,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = %s
                ORDER BY ordinal_position
                """,
                {'table_name': table_name}
            )

            columns = []
            for row in result['data']:
                column_info = {
                    'name': row['column_name'],
                    'type': row['data_type'],
                    'is_nullable': row['is_nullable'] == 'YES',
                    'default_value': row['column_default'],
                    'description': row.get('column_comment', ''),
                    'is_primary_key': row['column_key'] == 'PRI',
                    'is_unique': row['column_key'] == 'UNI',
                    'is_auto_increment': 'auto_increment' in (row.get('extra') or '').lower()
                }

                # 添加长度信息
                if row['character_maximum_length']:
                    column_info['max_length'] = row['character_maximum_length']
                if row['numeric_precision']:
                    column_info['precision'] = row['numeric_precision']
                if row['numeric_scale']:
                    column_info['scale'] = row['numeric_scale']

                columns.append(column_info)

            return columns

        except Exception as e:
            logger.error(f"获取MySQL表列信息失败: {e}")
            raise

    async def get_foreign_keys(self, table_name: str = None) -> List[Dict[str, Any]]:
        """获取外键信息"""
        try:
            if table_name:
                where_clause = "AND table_name = %s"
                params = {'table_name': table_name}
            else:
                where_clause = ""
                params = {}

            result = await self.execute_query(
                f"""
                SELECT
                    table_name,
                    column_name,
                    referenced_table_name,
                    referenced_column_name,
                    constraint_name
                FROM information_schema.key_column_usage
                WHERE table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                {where_clause}
                """,
                params
            )

            foreign_keys = []
            for row in result['data']:
                foreign_keys.append({
                    'column': row['column_name'],
                    'references_table': row['referenced_table_name'],
                    'references_column': row['referenced_column_name'],
                    'constraint_name': row['constraint_name']
                })

            return foreign_keys

        except Exception as e:
            logger.error(f"获取MySQL外键信息失败: {e}")
            return []

    async def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取示例数据"""
        try:
            result = await self.execute_query(
                f"SELECT * FROM `{table_name}` LIMIT %s",
                {'limit': limit}
            )
            return result['data']

        except Exception as e:
            logger.error(f"获取MySQL示例数据失败: {e}")
            return []

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            conn = await self.get_connection()
            await conn.ping()
            return True
        except Exception as e:
            logger.error(f"MySQL连接测试失败: {e}")
            return False


class SQLiteAdapter(DatabaseAdapter):
    """SQLite适配器实现"""

    def __init__(self, connection_string: str, tenant_id: str):
        super().__init__(connection_string, tenant_id)
        self.connection = None
        # 解析连接字符串获取数据库文件路径
        self._db_path = self._parse_connection_string(connection_string)

    def _parse_connection_string(self, connection_string: str) -> str:
        """解析SQLite连接字符串"""
        if connection_string.startswith("sqlite:///"):
            return connection_string[10:]
        elif connection_string.startswith("sqlite://"):
            path = connection_string[9:]
            return path if path else ":memory:"
        return connection_string

    def _detect_database_type(self) -> DatabaseType:
        """检测为SQLite"""
        return DatabaseType.SQLITE

    async def get_connection(self):
        """获取SQLite连接"""
        import aiosqlite

        if self.connection is None:
            self.connection = await aiosqlite.connect(self._db_path)
            await self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.row_factory = aiosqlite.Row
        return self.connection

    async def close_connection(self, connection=None):
        """关闭SQLite连接"""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def execute_query(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """执行查询"""
        try:
            conn = await self.get_connection()

            if params:
                cursor = await conn.execute(query, list(params.values()))
            else:
                cursor = await conn.execute(query)

            query_upper = query.strip().upper()
            if query_upper.startswith(('SELECT', 'PRAGMA')):
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, row)) for row in rows]
                result = {
                    'success': True,
                    'data': data,
                    'row_count': len(data),
                    'columns': columns
                }
            else:
                await conn.commit()
                result = {
                    'success': True,
                    'data': [],
                    'row_count': cursor.rowcount,
                    'columns': []
                }

            await cursor.close()
            return result

        except Exception as e:
            logger.error(f"SQLite查询执行失败: {e}")
            return {'success': False, 'error': str(e), 'data': [], 'row_count': 0}

    async def get_schema_info(self, table_name: str = None) -> Dict[str, Any]:
        """获取数据库结构信息"""
        try:
            schema_info = {'database_type': 'sqlite', 'tables': {}}

            # 获取所有表
            tables = await self.get_tables()
            if table_name:
                tables = [t for t in tables if t['name'] == table_name]

            for table in tables:
                tname = table['name']
                columns = await self.get_columns(tname)
                foreign_keys = await self.get_foreign_keys(tname)

                schema_info['tables'][tname] = {
                    'type': table.get('type', 'table'),
                    'columns': columns,
                    'foreign_keys': foreign_keys
                }

            return schema_info

        except Exception as e:
            logger.error(f"获取SQLite结构信息失败: {e}")
            raise

    async def get_tables(self) -> List[Dict[str, Any]]:
        """获取所有表信息"""
        try:
            result = await self.execute_query("""
                SELECT name, type
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)

            tables = []
            for row in result['data']:
                # 获取行数
                count_result = await self.execute_query(
                    f"SELECT COUNT(*) as cnt FROM \"{row['name']}\""
                )
                row_count = count_result['data'][0]['cnt'] if count_result['data'] else 0

                tables.append({
                    'name': row['name'],
                    'type': row['type'],
                    'row_count': row_count
                })

            return tables

        except Exception as e:
            logger.error(f"获取SQLite表列表失败: {e}")
            return []

    async def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            result = await self.execute_query(f"PRAGMA table_info('{table_name}')")

            columns = []
            for row in result['data']:
                columns.append({
                    'column_name': row['name'],
                    'data_type': row['type'],
                    'is_nullable': row['notnull'] == 0,
                    'default_value': row['dflt_value'],
                    'is_primary_key': row['pk'] == 1
                })

            return columns

        except Exception as e:
            logger.error(f"获取SQLite表列信息失败: {e}")
            raise

    async def get_foreign_keys(self, table_name: str = None) -> List[Dict[str, Any]]:
        """获取外键信息"""
        try:
            if not table_name:
                # 获取所有表的外键
                tables = await self.get_tables()
                all_fks = []
                for table in tables:
                    fks = await self.get_foreign_keys(table['name'])
                    for fk in fks:
                        fk['table_name'] = table['name']
                    all_fks.extend(fks)
                return all_fks

            result = await self.execute_query(f"PRAGMA foreign_key_list('{table_name}')")

            foreign_keys = []
            for row in result['data']:
                foreign_keys.append({
                    'column': row['from'],
                    'references_table': row['table'],
                    'references_column': row['to'],
                    'constraint_name': f"fk_{table_name}_{row['from']}"
                })

            return foreign_keys

        except Exception as e:
            logger.error(f"获取SQLite外键信息失败: {e}")
            return []

    async def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取示例数据"""
        try:
            result = await self.execute_query(
                f"SELECT * FROM \"{table_name}\" LIMIT ?",
                {'limit': limit}
            )
            return result['data']

        except Exception as e:
            logger.error(f"获取SQLite示例数据失败: {e}")
            return []

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT 1")
            await cursor.fetchone()
            await cursor.close()
            return True
        except Exception as e:
            logger.error(f"SQLite连接测试失败: {e}")
            return False


class DatabaseAdapterFactory:
    """数据库适配器工厂"""

    @staticmethod
    def create_adapter(connection_string: str, tenant_id: str) -> DatabaseAdapter:
        """创建数据库适配器"""
        # 根据连接字符串检测数据库类型
        if connection_string.startswith(("postgresql://", "postgresql+asyncpg://")):
            return PostgreSQLAdapter(connection_string, tenant_id)
        elif connection_string.startswith("mysql://"):
            return MySQLAdapter(connection_string, tenant_id)
        elif connection_string.startswith("sqlite://"):
            return SQLiteAdapter(connection_string, tenant_id)
        else:
            # 默认使用PostgreSQL
            logger.warning(f"未知的数据库连接类型，默认使用PostgreSQL: {connection_string}")
            return PostgreSQLAdapter(connection_string, tenant_id)

    @staticmethod
    def get_supported_databases() -> List[Dict[str, Any]]:
        """获取支持的数据库列表"""
        return [
            {
                "type": DatabaseType.POSTGRESQL,
                "name": "PostgreSQL",
                "description": "功能强大的开源关系型数据库",
                "status": "fully_supported",
                "features": list(DatabaseCapability(DatabaseType.POSTGRESQL).features)
            },
            {
                "type": DatabaseType.MYSQL,
                "name": "MySQL",
                "description": "流行的开源关系型数据库",
                "status": "fully_supported",
                "features": list(DatabaseCapability(DatabaseType.MYSQL).features)
            },
            {
                "type": DatabaseType.SQLITE,
                "name": "SQLite",
                "description": "轻量级嵌入式数据库",
                "status": "fully_supported",
                "features": list(DatabaseCapability(DatabaseType.SQLITE).features)
            }
        ]

    @staticmethod
    def detect_database_type(connection_string: str) -> DatabaseType:
        """检测数据库类型"""
        if connection_string.startswith(("postgresql://", "postgresql+asyncpg://")):
            return DatabaseType.POSTGRESQL
        elif connection_string.startswith("mysql://"):
            return DatabaseType.MYSQL
        elif connection_string.startswith("sqlite://"):
            return DatabaseType.SQLITE
        else:
            # 默认返回PostgreSQL
            return DatabaseType.POSTGRESQL