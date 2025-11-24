"""
数据库适配器工厂
提供统一的数据库连接管理、适配器创建和验证功能
"""

from typing import Dict, Any, Optional, List, Type
from urllib.parse import urlparse
import re
import logging
from dataclasses import dataclass

from .database_interface import (
    DatabaseInterface, DatabaseType, PostgreSQLAdapter,
    MySQLAdapter, SQLiteDatabaseAdapter
)

logger = logging.getLogger(__name__)


@dataclass
class DatabaseCredentials:
    """数据库连接凭据"""
    host: str
    port: int
    database_name: str
    username: str
    password: str
    database_type: DatabaseType
    ssl_mode: Optional[str] = None
    additional_params: Dict[str, Any] = None


class DatabaseConnectionValidator:
    """数据库连接验证器"""

    @staticmethod
    def validate_connection_string(connection_string: str) -> bool:
        """
        验证数据库连接字符串格式

        Args:
            connection_string: 数据库连接字符串

        Returns:
            bool: 验证结果
        """
        try:
            # 解析连接字符串
            parsed = urlparse(connection_string)

            if not parsed.scheme:
                logger.error("连接字符串缺少协议")
                return False

            if not parsed.hostname:
                logger.error("连接字符串缺少主机名")
                return False

            if not parsed.path or not parsed.path.lstrip('/'):
                logger.error("连接字符串缺少数据库名")
                return False

            return True

        except Exception as e:
            logger.error(f"连接字符串验证失败: {e}")
            return False

    @staticmethod
    def parse_connection_string(connection_string: str) -> Optional[DatabaseCredentials]:
        """
        解析数据库连接字符串

        Args:
            connection_string: 数据库连接字符串

        Returns:
            DatabaseCredentials: 解析后的连接凭据
        """
        try:
            parsed = urlparse(connection_string)

            # 确定数据库类型
            scheme = parsed.scheme.lower()
            if scheme in ['postgresql', 'postgres']:
                db_type = DatabaseType.POSTGRESQL
                default_port = 5432
            elif scheme == 'mysql':
                db_type = DatabaseType.MYSQL
                default_port = 3306
            elif scheme == 'sqlite':
                db_type = DatabaseType.SQLITE
                default_port = 0
            else:
                logger.error(f"不支持的数据库类型: {scheme}")
                return None

            # 对于SQLite，路径就是文件路径
            if db_type == DatabaseType.SQLITE:
                return DatabaseCredentials(
                    host="",
                    port=0,
                    database_name=parsed.path,
                    username="",
                    password="",
                    database_type=db_type
                )

            # 提取连接参数
            port = parsed.port or default_port
            database_name = parsed.path.lstrip('/')

            # 解析查询参数
            query_params = {}
            if parsed.query:
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value

            # 提取SSL模式
            ssl_mode = query_params.pop('sslmode', None)

            return DatabaseCredentials(
                host=parsed.hostname or "",
                port=port,
                database_name=database_name,
                username=parsed.username or "",
                password=parsed.password or "",
                database_type=db_type,
                ssl_mode=ssl_mode,
                additional_params=query_params
            )

        except Exception as e:
            logger.error(f"解析连接字符串失败: {e}")
            return None

    @staticmethod
    def validate_sql_safety(query: str) -> tuple[bool, Optional[str]]:
        """
        验证SQL查询安全性

        Args:
            query: SQL查询语句

        Returns:
            tuple: (是否安全, 错误信息)
        """
        if not query:
            return False, "查询不能为空"

        # 转换为大写进行关键词检查
        query_upper = query.upper().strip()

        # 检查是否以SELECT开头
        if not query_upper.startswith('SELECT'):
            return False, "只允许SELECT查询"

        # 检查危险关键词
        dangerous_patterns = [
            r'\bDROP\b',
            r'\bDELETE\b',
            r'\bUPDATE\b',
            r'\bINSERT\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'\bTRUNCATE\b',
            r'\bEXEC\b',
            r'\bEXECUTE\b',
            r'\bUNION\b.*\bSELECT\b',  # 简单的UNION注入检查
            r';\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)',  # 多语句注入
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"检测到不安全的SQL模式: {pattern}"

        # 检查查询复杂度（简单检查）
        if query_upper.count('SELECT') > 5:
            return False, "查询过于复杂，可能包含嵌套子查询"

        if query_upper.count('JOIN') > 10:
            return False, "JOIN数量过多，可能影响性能"

        return True, None


class DatabaseAdapterFactory:
    """数据库适配器工厂"""

    # 注册的适配器类型
    _adapters: Dict[DatabaseType, Type[DatabaseInterface]] = {
        DatabaseType.POSTGRESQL: PostgreSQLAdapter,
        DatabaseType.MYSQL: MySQLAdapter,
        DatabaseType.SQLITE: SQLiteDatabaseAdapter,
    }

    @classmethod
    def register_adapter(cls, db_type: DatabaseType, adapter_class: Type[DatabaseInterface]):
        """
        注册新的数据库适配器

        Args:
            db_type: 数据库类型
            adapter_class: 适配器类
        """
        cls._adapters[db_type] = adapter_class
        logger.info(f"注册数据库适配器: {db_type.value} -> {adapter_class.__name__}")

    @classmethod
    def get_supported_types(cls) -> List[DatabaseType]:
        """获取支持的数据库类型列表"""
        return list(cls._adapters.keys())

    @classmethod
    def create_adapter(cls, connection_string: str, **kwargs) -> DatabaseInterface:
        """
        创建数据库适配器实例

        Args:
            connection_string: 数据库连接字符串
            **kwargs: 额外的配置参数

        Returns:
            DatabaseInterface: 数据库适配器实例
        """
        # 验证连接字符串
        if not DatabaseConnectionValidator.validate_connection_string(connection_string):
            raise ValueError("无效的数据库连接字符串")

        # 解析连接字符串
        credentials = DatabaseConnectionValidator.parse_connection_string(connection_string)
        if not credentials:
            raise ValueError("无法解析数据库连接字符串")

        # 检查是否支持该数据库类型
        if credentials.database_type not in cls._adapters:
            raise ValueError(f"不支持的数据库类型: {credentials.database_type.value}")

        # 获取适配器类
        adapter_class = cls._adapters[credentials.database_type]

        # 创建适配器实例
        adapter = adapter_class(connection_string, **kwargs)

        logger.info(f"创建数据库适配器: {credentials.database_type.value}")
        return adapter

    @classmethod
    async def create_and_connect(cls, connection_string: str, **kwargs) -> DatabaseInterface:
        """
        创建并连接数据库适配器

        Args:
            connection_string: 数据库连接字符串
            **kwargs: 额外的配置参数

        Returns:
            DatabaseInterface: 已连接的数据库适配器实例
        """
        adapter = cls.create_adapter(connection_string, **kwargs)

        if not await adapter.connect():
            raise ConnectionError(f"无法连接到数据库: {connection_string}")

        return adapter

    @classmethod
    async def test_connection(cls, connection_string: str, **kwargs) -> tuple[bool, Optional[str]]:
        """
        测试数据库连接

        Args:
            connection_string: 数据库连接字符串
            **kwargs: 额外的配置参数

        Returns:
            tuple: (连接成功, 错误信息)
        """
        try:
            adapter = cls.create_adapter(connection_string, **kwargs)
            success = await adapter.test_connection()

            if success:
                return True, None
            else:
                return False, "连接测试失败"

        except Exception as e:
            logger.error(f"数据库连接测试异常: {e}")
            return False, str(e)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self._connections: Dict[str, DatabaseInterface] = {}
        self.validator = DatabaseConnectionValidator()

    async def add_connection(self, connection_id: str, connection_string: str,
                           **kwargs) -> bool:
        """
        添加数据库连接

        Args:
            connection_id: 连接ID
            connection_string: 连接字符串
            **kwargs: 额外配置参数

        Returns:
            bool: 添加成功
        """
        try:
            adapter = await DatabaseAdapterFactory.create_and_connect(
                connection_string, **kwargs
            )
            self._connections[connection_id] = adapter
            logger.info(f"添加数据库连接: {connection_id}")
            return True

        except Exception as e:
            logger.error(f"添加数据库连接失败: {e}")
            return False

    async def remove_connection(self, connection_id: str) -> bool:
        """
        移除数据库连接

        Args:
            connection_id: 连接ID

        Returns:
            bool: 移除成功
        """
        try:
            if connection_id in self._connections:
                adapter = self._connections[connection_id]
                await adapter.disconnect()
                del self._connections[connection_id]
                logger.info(f"移除数据库连接: {connection_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"移除数据库连接失败: {e}")
            return False

    def get_connection(self, connection_id: str) -> Optional[DatabaseInterface]:
        """
        获取数据库连接

        Args:
            connection_id: 连接ID

        Returns:
            DatabaseInterface: 数据库适配器实例
        """
        return self._connections.get(connection_id)

    def list_connections(self) -> List[str]:
        """列出所有连接ID"""
        return list(self._connections.keys())

    async def test_all_connections(self) -> Dict[str, tuple[bool, Optional[str]]]:
        """
        测试所有数据库连接

        Returns:
            Dict: 连接ID -> (测试结果, 错误信息)
        """
        results = {}
        for connection_id, adapter in self._connections.items():
            try:
                success = await adapter.test_connection()
                results[connection_id] = (success, None if success else "连接失败")
            except Exception as e:
                results[connection_id] = (False, str(e))

        return results

    async def cleanup_all(self):
        """清理所有数据库连接"""
        for connection_id in list(self._connections.keys()):
            await self.remove_connection(connection_id)

    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        获取连接信息

        Args:
            connection_id: 连接ID

        Returns:
            Dict: 连接信息
        """
        adapter = self.get_connection(connection_id)
        if not adapter:
            return None

        try:
            schema_info = await adapter.get_schema_info()
            return {
                "connection_id": connection_id,
                "database_type": adapter.get_database_type().value,
                "database_name": schema_info.database_name,
                "table_count": len(schema_info.tables),
                "last_updated": schema_info.last_updated.isoformat() if schema_info.last_updated else None,
                "version": schema_info.version
            }
        except Exception as e:
            logger.error(f"获取连接信息失败: {e}")
            return {
                "connection_id": connection_id,
                "database_type": adapter.get_database_type().value,
                "error": str(e)
            }


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """获取全局数据库管理器"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def initialize_database_manager() -> DatabaseManager:
    """初始化全局数据库管理器"""
    global _db_manager
    _db_manager = DatabaseManager()
    logger.info("数据库管理器初始化完成")
    return _db_manager