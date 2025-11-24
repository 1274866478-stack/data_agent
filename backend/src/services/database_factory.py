"""
数据库适配器工厂
支持多种数据库类型的统一创建和管理
"""

import logging
from typing import Dict, Type, Optional
from urllib.parse import urlparse, parse_qs

from .database_interface import DatabaseInterface, PostgreSQLAdapter, MySQLAdapter, SQLiteDatabaseAdapter

logger = logging.getLogger(__name__)


class DatabaseAdapterFactory:
    """数据库适配器工厂类"""

    _adapters: Dict[str, Type[DatabaseInterface]] = {
        "postgresql": PostgreSQLAdapter,
        "postgres": PostgreSQLAdapter,  # 别名
        "mysql": MySQLAdapter,
        "sqlite": SQLiteDatabaseAdapter,
    }

    @classmethod
    def create_adapter(cls, db_type: str) -> DatabaseInterface:
        """
        创建数据库适配器实例

        Args:
            db_type: 数据库类型

        Returns:
            DatabaseInterface: 数据库适配器实例

        Raises:
            ValueError: 不支持的数据库类型
        """
        db_type = db_type.lower().strip()

        adapter_class = cls._adapters.get(db_type)
        if not adapter_class:
            supported_types = ", ".join(cls._adapters.keys())
            error_msg = f"不支持的数据库类型: {db_type}。支持的类型: {supported_types}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            adapter = adapter_class()
            logger.info(f"成功创建 {db_type} 数据库适配器")
            return adapter
        except Exception as e:
            logger.error(f"创建 {db_type} 数据库适配器失败: {e}")
            raise

    @classmethod
    def register_adapter(cls, db_type: str, adapter_class: Type[DatabaseInterface]):
        """
        注册新的数据库适配器

        Args:
            db_type: 数据库类型
            adapter_class: 适配器类
        """
        if not issubclass(adapter_class, DatabaseInterface):
            raise ValueError("适配器类必须继承自 DatabaseInterface")

        cls._adapters[db_type.lower()] = adapter_class
        logger.info(f"成功注册数据库适配器: {db_type} -> {adapter_class.__name__}")

    @classmethod
    def get_supported_types(cls) -> list:
        """
        获取支持的数据库类型列表

        Returns:
            list: 支持的数据库类型列表
        """
        return list(cls._adapters.keys())

    @classmethod
    def get_adapter_info(cls, db_type: str) -> Optional[Dict[str, any]]:
        """
        获取适配器信息

        Args:
            db_type: 数据库类型

        Returns:
            Optional[Dict]: 适配器信息或None
        """
        db_type = db_type.lower().strip()
        adapter_class = cls._adapters.get(db_type)

        if not adapter_class:
            return None

        try:
            # 创建临时实例获取信息
            temp_adapter = adapter_class()
            return {
                "type": db_type,
                "class_name": adapter_class.__name__,
                "dialect": temp_adapter.get_dialect(),
                "connection_template": temp_adapter.get_connection_template()
            }
        except Exception as e:
            logger.error(f"获取适配器信息失败: {e}")
            return None

    @classmethod
    def parse_connection_string(cls, connection_string: str) -> Dict[str, any]:
        """
        解析数据库连接字符串

        Args:
            connection_string: 数据库连接字符串

        Returns:
            Dict[str, any]: 解析结果
        """
        try:
            parsed = urlparse(connection_string)
            scheme = parsed.scheme.lower()

            # 标准化数据库类型
            if scheme in ["postgresql", "postgres"]:
                db_type = "postgresql"
            elif scheme == "mysql":
                db_type = "mysql"
            elif scheme == "sqlite":
                db_type = "sqlite"
            else:
                raise ValueError(f"不支持的数据库协议: {scheme}")

            # 解析参数
            params = parse_qs(parsed.query)
            processed_params = {}
            for key, values in params.items():
                processed_params[key] = values[0] if len(values) == 1 else values

            config = {
                "type": db_type,
                "scheme": scheme,
                "host": parsed.hostname,
                "port": parsed.port,
                "database": parsed.path.lstrip("/") if parsed.path else None,
                "username": parsed.username,
                "password": parsed.password,
                "params": processed_params
            }

            # SQLite特殊处理
            if db_type == "sqlite":
                config["database"] = connection_string.replace("sqlite:///", "")
                config["host"] = None
                config["port"] = None
                config["username"] = None
                config["password"] = None

            return config

        except Exception as e:
            logger.error(f"解析连接字符串失败: {e}")
            raise ValueError(f"无效的连接字符串: {str(e)}")

    @classmethod
    def build_connection_string(cls, config: Dict[str, any]) -> str:
        """
        构建数据库连接字符串

        Args:
            config: 连接配置

        Returns:
            str: 连接字符串
        """
        db_type = config.get("type", "").lower()

        if db_type == "sqlite":
            return f"sqlite:///{config.get('database', '')}"

        # PostgreSQL/MySQL
        host = config.get("host", "localhost")
        port = config.get("port")
        database = config.get("database", "")
        username = config.get("username", "")
        password = config.get("password", "")
        params = config.get("params", {})

        # 构建基础URL
        if db_type == "postgresql":
            scheme = "postgresql"
        elif db_type == "mysql":
            scheme = "mysql"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

        # 构建认证部分
        auth_part = ""
        if username:
            if password:
                auth_part = f"{username}:{password}@"
            else:
                auth_part = f"{username}@"

        # 构建主机部分
        host_part = host
        if port:
            host_part = f"{host}:{port}"

        # 构建数据库部分
        db_part = f"/{database}" if database else ""

        # 构建参数部分
        param_part = ""
        if params:
            param_list = [f"{k}={v}" for k, v in params.items()]
            param_part = f"?{'&'.join(param_list)}"

        return f"{scheme}://{auth_part}{host_part}{db_part}{param_part}"


class ConnectionStringValidator:
    """连接字符串验证器"""

    @staticmethod
    def validate_format(connection_string: str) -> Dict[str, any]:
        """
        验证连接字符串格式

        Args:
            connection_string: 数据库连接字符串

        Returns:
            Dict[str, any]: 验证结果
        """
        try:
            config = DatabaseAdapterFactory.parse_connection_string(connection_string)
            db_type = config["type"]

            # 基本格式验证
            if not db_type:
                return {
                    "valid": False,
                    "error": "无法识别数据库类型",
                    "suggestion": "请使用正确的连接字符串格式，如: postgresql://user:pass@host:port/dbname"
                }

            # 检查必需字段
            if db_type != "sqlite":
                if not config.get("host"):
                    return {
                        "valid": False,
                        "error": "缺少主机地址",
                        "suggestion": "请在连接字符串中提供主机地址"
                    }

                if not config.get("database"):
                    return {
                        "valid": False,
                        "error": "缺少数据库名",
                        "suggestion": "请在连接字符串中提供数据库名"
                    }

            return {
                "valid": True,
                "config": config,
                "db_type": db_type
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"连接字符串格式错误: {str(e)}",
                "suggestion": "请检查连接字符串格式是否正确"
            }

    @staticmethod
    def get_connection_templates() -> Dict[str, str]:
        """
        获取各种数据库的连接字符串模板

        Returns:
            Dict[str, str]: 连接字符串模板
        """
        return {
            "postgresql": "postgresql://[username[:password]@]host[:port]/database[?sslmode=require]",
            "mysql": "mysql://[username[:password]@]host[:port]/database[?charset=utf8mb4]",
            "sqlite": "sqlite:///path/to/database.db"
        }


# 全局工厂实例
db_factory = DatabaseAdapterFactory()
conn_validator = ConnectionStringValidator()