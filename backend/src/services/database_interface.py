"""
数据库接口抽象层
支持多种数据库类型的统一访问
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseInterface(ABC):
    """数据库接口抽象类"""

    @abstractmethod
    async def get_schema(self, connection_string: str, **kwargs) -> Dict[str, Any]:
        """获取数据库schema"""
        pass

    @abstractmethod
    async def execute_query(self, connection_string: str, query: str, **kwargs) -> Dict[str, Any]:
        """执行查询"""
        pass

    @abstractmethod
    def get_dialect(self) -> str:
        """获取数据库方言"""
        pass

    @abstractmethod
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """验证查询"""
        pass

    @abstractmethod
    async def test_connection(self, connection_string: str) -> Dict[str, Any]:
        """测试数据库连接"""
        pass

    @abstractmethod
    def get_connection_template(self) -> Dict[str, Any]:
        """获取连接字符串模板"""
        pass


class PostgreSQLAdapter(DatabaseInterface):
    """PostgreSQL数据库适配器"""

    def get_dialect(self) -> str:
        return "postgresql"

    def get_connection_template(self) -> Dict[str, Any]:
        return {
            "scheme": "postgresql",
            "default_port": 5432,
            "ssl_modes": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
            "connection_format": "postgresql://[user[:password]@][host][:port][/dbname][?param1=value1&...]"
        }

    async def get_schema(self, connection_string: str, **kwargs) -> Dict[str, Any]:
        """获取PostgreSQL数据库schema"""
        try:
            from sqlalchemy import create_engine, text
            import sqlalchemy as sa

            # 创建数据库连接
            engine = create_engine(connection_string)

            schema_info = {
                "database_type": "postgresql",
                "version": None,
                "tables": [],
                "views": [],
                "relationships": [],
                "indexes": [],
                "sample_data": {},
                "discovered_at": datetime.utcnow().isoformat()
            }

            with engine.connect() as conn:
                # 获取数据库版本
                version_result = conn.execute(text("SELECT version()"))
                schema_info["version"] = version_result.scalar()

                # 获取所有表
                tables_query = """
                SELECT
                    t.table_name,
                    t.table_type,
                    obj_description(c.oid) as table_comment
                FROM information_schema.tables t
                LEFT JOIN pg_class c ON c.relname = t.table_name
                WHERE t.table_schema = 'public'
                ORDER BY t.table_name
                """

                tables_result = conn.execute(text(tables_query))
                for row in tables_result:
                    table_name = row.table_name
                    table_info = {
                        "name": table_name,
                        "type": row.table_type.lower(),
                        "comment": row.table_comment,
                        "columns": []
                    }

                    # 获取列信息
                    columns_query = """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale,
                        col_description(pgc.oid, cols.ordinal_position) as column_comment
                    FROM information_schema.columns cols
                    LEFT JOIN pg_class pgc ON pgc.relname = cols.table_name
                    WHERE cols.table_schema = 'public' AND cols.table_name = :table_name
                    ORDER BY cols.ordinal_position
                    """

                    columns_result = conn.execute(text(columns_query), {"table_name": table_name})
                    for col_row in columns_result:
                        column_info = {
                            "name": col_row.column_name,
                            "type": col_row.data_type,
                            "nullable": col_row.is_nullable == "YES",
                            "default": col_row.column_default,
                            "max_length": col_row.character_maximum_length,
                            "precision": col_row.numeric_precision,
                            "scale": col_row.numeric_scale,
                            "comment": col_row.column_comment
                        }
                        table_info["columns"].append(column_info)

                    # 获取主键信息
                    pk_query = """
                    SELECT a.attname
                    FROM pg_constraint c
                    JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
                    WHERE c.conrelid = :table_name::regclass AND c.contype = 'p'
                    """

                    pk_result = conn.execute(text(pk_query), {"table_name": table_name})
                    primary_keys = [row.attname for row in pk_result]
                    if primary_keys:
                        table_info["primary_key"] = primary_keys

                    # 获取外键信息
                    fk_query = """
                    SELECT
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
                        AND tc.table_name = :table_name
                    """

                    fk_result = conn.execute(text(fk_query), {"table_name": table_name})
                    foreign_keys = []
                    for row in fk_result:
                        fk_info = {
                            "column": row.column_name,
                            "references_table": row.foreign_table_name,
                            "references_column": row.foreign_column_name
                        }
                        foreign_keys.append(fk_info)

                    if foreign_keys:
                        table_info["foreign_keys"] = foreign_keys

                    # 获取示例数据（前5行）
                    sample_query = text(f"SELECT * FROM {table_name} LIMIT 5")
                    try:
                        sample_result = conn.execute(sample_query)
                        sample_data = []
                        columns = [col for col in sample_result.keys()]

                        for row in sample_result:
                            row_data = {}
                            for i, value in enumerate(row):
                                if i < len(columns):
                                    row_data[columns[i]] = str(value) if value is not None else None
                            sample_data.append(row_data)

                        schema_info["sample_data"][table_name] = {
                            "columns": columns,
                            "data": sample_data
                        }
                    except Exception as e:
                        logger.warning(f"获取表 {table_name} 示例数据失败: {e}")

                    if table_info["type"] == "table":
                        schema_info["tables"].append(table_info)
                    else:
                        schema_info["views"].append(table_info)

                # 获取关系信息（基于外键）
                relationships_query = """
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                """

                relationships_result = conn.execute(text(relationships_query))
                for row in relationships_result:
                    relationship = {
                        "from_table": row.table_name,
                        "from_column": row.column_name,
                        "to_table": row.foreign_table_name,
                        "to_column": row.foreign_column_name,
                        "constraint_name": row.constraint_name,
                        "type": "foreign_key"
                    }
                    schema_info["relationships"].append(relationship)

            engine.dispose()
            return schema_info

        except Exception as e:
            logger.error(f"获取PostgreSQL schema失败: {e}")
            raise

    async def execute_query(self, connection_string: str, query: str, **kwargs) -> Dict[str, Any]:
        """执行PostgreSQL查询"""
        try:
            from sqlalchemy import create_engine, text
            import time

            engine = create_engine(connection_string)
            start_time = time.time()

            with engine.connect() as conn:
                result = conn.execute(text(query))
                execution_time = (time.time() - start_time) * 1000

                # 获取列信息
                columns = [col for col in result.keys()]

                # 获取数据
                data = []
                for row in result:
                    row_data = {}
                    for i, value in enumerate(row):
                        if i < len(columns):
                            # 处理特殊类型
                            if hasattr(value, 'isoformat'):  # datetime
                                row_data[columns[i]] = value.isoformat()
                            elif hasattr(value, 'tolist'):  # array types
                                row_data[columns[i]] = value.tolist()
                            else:
                                row_data[columns[i]] = value
                    data.append(row_data)

                # 获取受影响的行数
                if hasattr(result, 'rowcount'):
                    row_count = result.rowcount
                else:
                    row_count = len(data)

                return {
                    "columns": columns,
                    "data": data,
                    "row_count": row_count,
                    "execution_time_ms": execution_time,
                    "query": query
                }

        except Exception as e:
            logger.error(f"执行PostgreSQL查询失败: {e}")
            raise

    async def validate_query(self, query: str) -> Dict[str, Any]:
        """验证PostgreSQL查询"""
        try:
            # 基本SQL语法检查
            query_upper = query.upper().strip()

            # 检查危险操作
            dangerous_keywords = [
                "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
                "CREATE", "TRUNCATE", "EXECUTE", "GRANT", "REVOKE"
            ]

            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return {
                        "is_valid": False,
                        "errors": [f"不允许的操作: {keyword}"],
                        "warnings": []
                    }

            # 检查查询类型
            if not query_upper.startswith("SELECT"):
                return {
                    "is_valid": False,
                    "errors": ["只允许SELECT查询"],
                    "warnings": []
                }

            # 检查基本语法
            if "FROM" not in query_upper:
                return {
                    "is_valid": False,
                    "errors": ["SELECT查询缺少FROM子句"],
                    "warnings": []
                }

            return {
                "is_valid": True,
                "errors": [],
                "warnings": []
            }

        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"查询验证失败: {str(e)}"],
                "warnings": []
            }

    async def test_connection(self, connection_string: str) -> Dict[str, Any]:
        """测试PostgreSQL连接"""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(connection_string)

            with engine.connect() as conn:
                # 执行简单查询测试连接
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()

                # 获取数据库版本
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.scalar()

            engine.dispose()

            return {
                "success": True,
                "message": "PostgreSQL连接成功",
                "database_type": "postgresql",
                "version": version,
                "test_query_result": test_value
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"PostgreSQL连接失败: {str(e)}",
                "database_type": "postgresql",
                "version": None,
                "error": str(e)
            }


class MySQLAdapter(DatabaseInterface):
    """MySQL数据库适配器（准备实现）"""

    def get_dialect(self) -> str:
        return "mysql"

    def get_connection_template(self) -> Dict[str, Any]:
        return {
            "scheme": "mysql",
            "default_port": 3306,
            "ssl_modes": ["DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"],
            "connection_format": "mysql://[user[:password]@][host][:port][/dbname][?param1=value1&...]"
        }

    async def get_schema(self, connection_string: str, **kwargs) -> Dict[str, Any]:
        """获取MySQL数据库schema"""
        # TODO: 实现MySQL schema获取
        raise NotImplementedError("MySQL适配器尚未完全实现")

    async def execute_query(self, connection_string: str, query: str, **kwargs) -> Dict[str, Any]:
        """执行MySQL查询"""
        # TODO: 实现MySQL查询执行
        raise NotImplementedError("MySQL适配器尚未完全实现")

    async def validate_query(self, query: str) -> Dict[str, Any]:
        """验证MySQL查询"""
        # TODO: 实现MySQL查询验证
        raise NotImplementedError("MySQL适配器尚未完全实现")

    async def test_connection(self, connection_string: str) -> Dict[str, Any]:
        """测试MySQL连接"""
        # TODO: 实现MySQL连接测试
        raise NotImplementedError("MySQL适配器尚未完全实现")


class SQLiteDatabaseAdapter(DatabaseInterface):
    """SQLite数据库适配器（准备实现）"""

    def get_dialect(self) -> str:
        return "sqlite"

    def get_connection_template(self) -> Dict[str, Any]:
        return {
            "scheme": "sqlite",
            "connection_format": "sqlite:///[database_file_path]",
            "note": "SQLite使用文件路径，不支持网络连接"
        }

    async def get_schema(self, connection_string: str, **kwargs) -> Dict[str, Any]:
        """获取SQLite数据库schema"""
        # TODO: 实现SQLite schema获取
        raise NotImplementedError("SQLite适配器尚未完全实现")

    async def execute_query(self, connection_string: str, query: str, **kwargs) -> Dict[str, Any]:
        """执行SQLite查询"""
        # TODO: 实现SQLite查询执行
        raise NotImplementedError("SQLite适配器尚未完全实现")

    async def validate_query(self, query: str) -> Dict[str, Any]:
        """验证SQLite查询"""
        # TODO: 实现SQLite查询验证
        raise NotImplementedError("SQLite适配器尚未完全实现")

    async def test_connection(self, connection_string: str) -> Dict[str, Any]:
        """测试SQLite连接"""
        # TODO: 实现SQLite连接测试
        raise NotImplementedError("SQLite适配器尚未完全实现")