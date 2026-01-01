"""
# [CONNECTION_TEST_SERVICE] 连接测试服务

## [HEADER]
**文件名**: connection_test_service.py
**职责**: 测试数据库和文件连接的有效性，支持PostgreSQL/MySQL异步测试和MinIO文件验证
**作者**: Data Agent Team
**版本**: 1.0.0

## [INPUT]
- **connection_string: str** - 数据库连接字符串（明文）
- **db_type: str** - 数据库类型（postgresql, mysql, xlsx, csv, sqlite）
- **encrypted_connection_string: str** - 加密的连接字符串

## [OUTPUT]
- **ConnectionTestResult**: 连接测试结果对象
  - success: bool - 连接是否成功
  - message: str - 结果消息
  - response_time_ms: int - 响应时间（毫秒）
  - details: Dict - 详细信息
  - error_code: str - 错误代码

**上游依赖** (已读取源码):
- [./encryption_service.py](./encryption_service.py) - 加密服务
- [./minio_client.py](./minio_client.py) - MinIO服务

**下游依赖** (需要反向索引分析):
- [../api/v1/endpoints/data_sources.py](../api/v1/endpoints/data_sources.py) - 数据源API端点

**调用方**:
- 数据源连接测试API
- 数据源创建验证
- 数据源健康检查

## [STATE]
- **超时配置**: test_timeout=10秒
- **可选驱动**: asyncpg（异步PostgreSQL）, psycopg2, mysql.connector
- **错误代码**: DB_CONN_001（连接失败）, DB_CONN_002（认证失败）, DB_CONN_003（数据库不存在）, DB_CONN_004（超时）
- **正则解析**: PostgreSQL和MySQL连接字符串解析
- **异步测试**: PostgreSQL使用asyncpg异步连接
- **线程池执行**: MySQL使用loop.run_in_executor执行同步测试

## [SIDE-EFFECTS]
- **数据库连接**: asyncpg.connect, mysql.connector.connect
- **异步操作**: asyncio.wait_for超时控制
- **MinIO操作**: check_connection, list_files, download_file（文件测试）
- **线程池操作**: loop.run_in_executor（MySQL同步测试）
- **查询执行**: SELECT 1测试查询
- **数据库信息获取**: server_version, database_name, current_user
- **响应时间计算**: time.time()差值×1000

## [POS]
**路径**: backend/src/app/services/connection_test_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 encryption_service, minio_client
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .encryption_service import encryption_service

logger = logging.getLogger(__name__)

# 可选导入数据库驱动
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    logger.warning("asyncpg未安装,异步PostgreSQL连接功能将不可用")
    asyncpg = None
    ASYNCPG_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    logger.warning("psycopg2未安装,同步PostgreSQL连接功能将不可用")
    psycopg2 = None
    DictCursor = None
    PSYCOPG2_AVAILABLE = False


class ConnectionTestResult:
    """连接测试结果类"""

    def __init__(
        self,
        success: bool,
        message: str,
        response_time_ms: int = 0,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.response_time_ms = response_time_ms
        self.details = details or {}
        self.error_code = error_code
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat()
        }


class ConnectionTestService:
    """连接测试服务类"""

    def __init__(self):
        """初始化连接测试服务"""
        self.encryption_service = encryption_service
        self.test_timeout = 10  # 10秒超时
        logger.info("Connection test service initialized")

    async def test_connection(
        self,
        connection_string: str,
        db_type: str = "postgresql"
    ) -> ConnectionTestResult:
        """
        测试数据库连接

        Args:
            connection_string: 数据库连接字符串（明文）
            db_type: 数据库类型

        Returns:
            连接测试结果
        """
        logger.info(f"Testing {db_type} connection")
        start_time = time.time()

        try:
            if db_type == "postgresql":
                result = await self._test_postgresql_connection(connection_string)
            elif db_type == "mysql":
                result = await self._test_mysql_connection(connection_string)
            elif db_type in ["xlsx", "xls", "csv", "sqlite"]:
                # 文件类型的数据源，测试文件是否存在
                result = await self._test_file_connection(connection_string, db_type)
            else:
                result = ConnectionTestResult(
                    success=False,
                    message=f"Unsupported database type: {db_type}",
                    error_code="UNSUPPORTED_DB_TYPE"
                )

            # 计算响应时间
            response_time = int((time.time() - start_time) * 1000)
            result.response_time_ms = response_time

            logger.info(f"Connection test completed in {response_time}ms: {result.success}")
            return result

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test failed after {response_time}ms: {e}")

            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                response_time_ms=response_time,
                error_code="TEST_EXECUTION_ERROR"
            )

    async def test_encrypted_connection(
        self,
        encrypted_connection_string: str,
        db_type: str = "postgresql"
    ) -> ConnectionTestResult:
        """
        测试加密的数据库连接

        Args:
            encrypted_connection_string: 加密的连接字符串
            db_type: 数据库类型

        Returns:
            连接测试结果
        """
        try:
            # 解密连接字符串
            connection_string = self.encryption_service.decrypt_connection_string(
                encrypted_connection_string
            )
            return await self.test_connection(connection_string, db_type)
        except Exception as e:
            logger.error(f"Failed to decrypt connection string for testing: {e}")
            return ConnectionTestResult(
                success=False,
                message="Failed to decrypt connection string",
                error_code="DECRYPTION_ERROR"
            )

    async def _test_postgresql_connection(self, connection_string: str) -> ConnectionTestResult:
        """
        测试PostgreSQL连接

        Args:
            connection_string: PostgreSQL连接字符串

        Returns:
            连接测试结果
        """
        if not ASYNCPG_AVAILABLE:
            return ConnectionTestResult(
                success=False,
                message="asyncpg未安装,无法测试PostgreSQL连接",
                error_code="ASYNCPG_NOT_AVAILABLE"
            )

        try:
            # 验证连接字符串格式
            parsed_info = self._parse_postgresql_connection_string(connection_string)
            if not parsed_info:
                return ConnectionTestResult(
                    success=False,
                    message="Invalid PostgreSQL connection string format",
                    error_code="INVALID_CONNECTION_FORMAT"
                )

            # 使用asyncpg进行异步连接测试
            try:
                conn = await asyncio.wait_for(
                    asyncpg.connect(connection_string),
                    timeout=self.test_timeout
                )

                # 执行简单查询测试
                await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=self.test_timeout
                )

                # 获取数据库信息
                db_info = await self._get_postgresql_info(conn)

                await conn.close()

                return ConnectionTestResult(
                    success=True,
                    message="PostgreSQL connection successful",
                    details={
                        "database_type": "postgresql",
                        "server_version": db_info.get("server_version"),
                        "database_name": db_info.get("database_name"),
                        "current_user": db_info.get("current_user"),
                        "connection_info": {
                            "host": parsed_info.get("host"),
                            "port": parsed_info.get("port"),
                            "database": parsed_info.get("database")
                        }
                    }
                )

            except asyncio.TimeoutError:
                return ConnectionTestResult(
                    success=False,
                    message="Connection timeout",
                    error_code="DB_CONN_004"
                )

            except asyncpg.exceptions.InvalidPasswordError:
                return ConnectionTestResult(
                    success=False,
                    message="Database authentication failed",
                    error_code="DB_CONN_002"
                )

            except asyncpg.exceptions.InvalidCatalogNameError:
                return ConnectionTestResult(
                    success=False,
                    message="Database does not exist",
                    error_code="DB_CONN_003"
                )

            except asyncpg.exceptions.ConnectionFailureError as e:
                error_msg = str(e).lower()
                if "connection refused" in error_msg:
                    return ConnectionTestResult(
                        success=False,
                        message="Connection refused - check if PostgreSQL is running",
                        error_code="DB_CONN_001"
                    )
                elif "timeout" in error_msg:
                    return ConnectionTestResult(
                        success=False,
                        message="Connection timeout",
                        error_code="DB_CONN_004"
                    )
                else:
                    return ConnectionTestResult(
                        success=False,
                        message=f"Unable to connect to database: {str(e)}",
                        error_code="DB_CONN_001"
                    )

        except Exception as e:
            logger.error(f"PostgreSQL connection test error: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {str(e)}",
                error_code="DB_CONN_001"
            )

    async def _test_mysql_connection(self, connection_string: str) -> ConnectionTestResult:
        """
        测试MySQL连接（同步方式，因为psycopg2不支持异步）

        Args:
            connection_string: MySQL连接字符串

        Returns:
            连接测试结果
        """
        try:
            # 验证连接字符串格式
            parsed_info = self._parse_mysql_connection_string(connection_string)
            if not parsed_info:
                return ConnectionTestResult(
                    success=False,
                    message="Invalid MySQL connection string format",
                    error_code="INVALID_CONNECTION_FORMAT"
                )

            # 在线程池中执行同步MySQL连接测试
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_mysql_test,
                connection_string,
                parsed_info
            )
            return result

        except Exception as e:
            logger.error(f"MySQL connection test error: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"MySQL connection test failed: {str(e)}",
                error_code="DB_CONN_001"
            )

    def _sync_mysql_test(self, connection_string: str, parsed_info: Dict[str, Any]) -> ConnectionTestResult:
        """同步MySQL连接测试"""
        try:
            # 这里应该使用MySQL连接器，但为了示例使用psycopg2的接口
            # 实际实现需要安装mysql-connector-python或PyMySQL
            import mysql.connector
            from mysql.connector import Error

            conn = mysql.connector.connect(
                host=parsed_info["host"],
                port=parsed_info["port"],
                user=parsed_info["username"],
                password=parsed_info["password"],
                database=parsed_info["database"],
                connection_timeout=self.test_timeout
            )

            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

            # 获取数据库信息
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return ConnectionTestResult(
                success=True,
                message="MySQL connection successful",
                details={
                    "database_type": "mysql",
                    "server_version": version,
                    "database_name": parsed_info["database"],
                    "connection_info": {
                        "host": parsed_info["host"],
                        "port": parsed_info["port"],
                        "database": parsed_info["database"]
                    }
                }
            )

        except ImportError:
            return ConnectionTestResult(
                success=False,
                message="MySQL connector not installed",
                error_code="MYSQL_CONNECTOR_MISSING"
            )

        except Error as e:
            error_msg = str(e).lower()
            if "access denied" in error_msg:
                return ConnectionTestResult(
                    success=False,
                    message="MySQL authentication failed",
                    error_code="DB_CONN_002"
                )
            elif "unknown database" in error_msg:
                return ConnectionTestResult(
                    success=False,
                    message="MySQL database does not exist",
                    error_code="DB_CONN_003"
                )
            elif "connection refused" in error_msg:
                return ConnectionTestResult(
                    success=False,
                    message="MySQL connection refused",
                    error_code="DB_CONN_001"
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"MySQL connection failed: {str(e)}",
                    error_code="DB_CONN_001"
                )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"MySQL connection test failed: {str(e)}",
                error_code="DB_CONN_001"
            )

    async def _get_postgresql_info(self, conn) -> Dict[str, Any]:
        """获取PostgreSQL数据库信息"""
        try:
            # 获取服务器版本
            version = await conn.fetchval("SELECT version()")

            # 获取当前数据库名
            database_name = await conn.fetchval("SELECT current_database()")

            # 获取当前用户
            current_user = await conn.fetchval("SELECT current_user")

            return {
                "server_version": version,
                "database_name": database_name,
                "current_user": current_user
            }
        except Exception as e:
            logger.warning(f"Failed to get PostgreSQL info: {e}")
            return {}

    def _parse_postgresql_connection_string(self, connection_string: str) -> Optional[Dict[str, Any]]:
        """解析PostgreSQL连接字符串"""
        try:
            import re
            pattern = r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/([^/]+)"
            match = re.match(pattern, connection_string)

            if match:
                return {
                    "username": match.group(1),
                    "password": match.group(2),
                    "host": match.group(3),
                    "port": int(match.group(4)),
                    "database": match.group(5)
                }
            return None
        except Exception:
            return None

    def _parse_mysql_connection_string(self, connection_string: str) -> Optional[Dict[str, Any]]:
        """解析MySQL连接字符串"""
        try:
            import re
            pattern = r"mysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^/]+)"
            match = re.match(pattern, connection_string)

            if match:
                return {
                    "username": match.group(1),
                    "password": match.group(2),
                    "host": match.group(3),
                    "port": int(match.group(4)),
                    "database": match.group(5)
                }
            return None
        except Exception:
            return None

    async def _test_file_connection(self, connection_string: str, db_type: str) -> ConnectionTestResult:
        """
        测试文件类型数据源连接（验证MinIO中的文件是否存在）

        Args:
            connection_string: 文件路径（格式：file://... 或直接路径）
            db_type: 文件类型（xlsx, xls, csv, sqlite）

        Returns:
            连接测试结果
        """
        try:
            from .minio_client import minio_service

            # 解析存储路径
            if connection_string.startswith("file://"):
                storage_path = connection_string[7:]  # 去掉 "file://" 前缀
            else:
                storage_path = connection_string

            # 处理本地存储的情况
            if storage_path.startswith("local://"):
                return ConnectionTestResult(
                    success=False,
                    message="本地文件存储暂不支持连接测试",
                    error_code="LOCAL_STORAGE_NOT_TESTABLE",
                    details={"storage_type": "local", "path": storage_path}
                )

            # 检查MinIO连接
            if not minio_service.check_connection():
                return ConnectionTestResult(
                    success=False,
                    message="无法连接到文件存储服务",
                    error_code="STORAGE_CONNECTION_FAILED"
                )

            # 尝试从MinIO获取文件信息（不下载完整文件）
            bucket_name = "data-sources"

            # 尝试列出文件来验证是否存在
            try:
                files = minio_service.list_files(bucket_name=bucket_name, prefix=storage_path)
                file_exists = any(f.get("name") == storage_path for f in files)

                if not file_exists:
                    # 直接尝试下载一小部分来验证
                    file_data = minio_service.download_file(
                        bucket_name=bucket_name,
                        object_name=storage_path
                    )
                    file_exists = file_data is not None

            except Exception as e:
                logger.warning(f"检查文件时出错: {e}")
                file_exists = False

            if file_exists:
                return ConnectionTestResult(
                    success=True,
                    message=f"文件存在且可访问 ({db_type.upper()})",
                    details={
                        "file_type": db_type,
                        "storage_path": storage_path,
                        "bucket": bucket_name
                    }
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"文件不存在或无法访问: {storage_path}",
                    error_code="FILE_NOT_FOUND",
                    details={"storage_path": storage_path}
                )

        except ImportError:
            return ConnectionTestResult(
                success=False,
                message="MinIO客户端未配置",
                error_code="MINIO_NOT_AVAILABLE"
            )
        except Exception as e:
            logger.error(f"文件连接测试失败: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"文件连接测试失败: {str(e)}",
                error_code="FILE_TEST_ERROR"
            )

    def get_supported_database_types(self) -> Dict[str, Any]:
        """获取支持的数据库类型信息"""
        return {
            "supported_types": [
                {
                    "type": "postgresql",
                    "display_name": "PostgreSQL",
                    "description": "PostgreSQL 数据库连接",
                    "default_port": 5432,
                    "required_fields": ["host", "port", "database", "username", "password"],
                    "connection_format": "postgresql://{username}:{password}@{host}:{port}/{database}"
                },
                {
                    "type": "mysql",
                    "display_name": "MySQL",
                    "description": "MySQL 数据库连接",
                    "default_port": 3306,
                    "required_fields": ["host", "port", "database", "username", "password"],
                    "connection_format": "mysql://{username}:{password}@{host}:{port}/{database}"
                }
            ],
            "test_timeout_seconds": self.test_timeout
        }


# 全局连接测试服务实例
connection_test_service = ConnectionTestService()