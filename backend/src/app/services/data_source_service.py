"""
# [DATA_SOURCE_SERVICE] 数据源管理服务

## [HEADER]
**文件名**: data_source_service.py
**职责**: 实现数据源连接的CRUD操作、租户隔离、连接字符串加密解密、连接解析和批量管理功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 数据源管理服务

## [INPUT]
- **tenant_id: str** - 租户ID（强制隔离）
- **name: str** - 数据源名称
- **connection_string: str** - 数据库连接字符串（明文，将被加密）
- **db: Session** - SQLAlchemy数据库会话（依赖注入）
- **db_type: str** - 数据库类型（postgresql, mysql等，默认postgresql）
- **host: Optional[str]** - 主机地址
- **port: Optional[int]** - 端口号
- **database_name: Optional[str]** - 数据库名称
- **update_data: Dict[str, Any]** - 更新数据字典
- **active_only: bool** - 是否只获取活跃数据源（默认True）
- **skip: int** - 分页跳过记录数（默认0）
- **limit: int** - 分页限制记录数（默认100）

## [OUTPUT]
- **DataSourceConnection**: 数据源连接对象（create, get_by_id, update）
- **List[DataSourceConnection]**: 数据源连接列表（get_data_sources）
- **bool**: 操作成功/失败（delete_data_source）
- **str**: 解密后的连接字符串（get_decrypted_connection_string）
- **Dict[str, Any]**: 解析后的连接信息（_parse_connection_string）
  - username: str - 用户名
  - password: str - 密码
  - host: str - 主机
  - port: int - 端口
  - database: str - 数据库名

**上游依赖** (已读取源码):
- [./data/models.py](./data/models.py) - 数据模型（DataSourceConnection, Tenant, DataSourceConnectionStatus）
- [./encryption_service.py](./encryption_service.py) - 加密服务（connection_string加密解密）

**下游依赖** (需要反向索引分析):
- [../api/v1/endpoints/data_sources.py](../api/v1/endpoints/data_sources.py) - 数据源API端点
- [connection_test_service.py](./connection_test_service.py) - 连接测试服务

**调用方**:
- 数据源创建流程
- 数据源管理API
- 连接测试操作
- Agent查询（需要解密连接字符串）

## [STATE]
- **加密服务**: 通过encryption_service加密连接字符串
- **租户隔离**: 所有操作强制过滤tenant_id
- **软删除策略**: 使用status=INACTIVE标记删除
- **名称唯一性**: 同一租户下名称唯一检查
- **连接解析**: 自动解析PostgreSQL和MySQL连接字符串
- **数据库会话**: 通过依赖注入的db参数管理事务

## [SIDE-EFFECTS]
- **数据库事务**: commit操作持久化变更（create, update, delete）
- **加密操作**: encryption_service.encrypt_connection_string（存储前）
- **解密操作**: 连接字符串属性访问时自动解密（模型层混合属性）
- **连接解析**: 正则匹配提取连接信息（PostgreSQL/MySQL）
- **查询过滤**: 自动过滤INACTIVE状态的记录（active_only=True时）
- **异常抛出**: 租户不存在、名称重复、数据源不存在时抛出ValueError
- **时间戳更新**: updated_at自动更新

## [POS]
**路径**: backend/src/app/services/data_source_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 data.models 和 encryption_service
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from dataclasses import dataclass

try:
    from ..data.models import DataSourceConnection, Tenant, DataSourceConnectionStatus
except ImportError as e:
    logging.error(f"Failed to import models: {e}")
    DataSourceConnection = None
    Tenant = None
    DataSourceConnectionStatus = None

try:
    from .encryption_service import encryption_service
except ImportError as e:
    logging.error(f"Failed to import encryption service: {e}")
    encryption_service = None

logger = logging.getLogger(__name__)


# ============================================================================
# 数据源连接信息数据类
# ============================================================================

@dataclass
class DataSourceConnectionInfo:
    """
    数据源连接信息（用于AgentV2）

    Attributes:
        connection_type: str - 连接类型 ("excel", "postgresql", "mysql")
        connection_string: Optional[str] - 数据库连接字符串（解密后）
        file_path: Optional[str] - Excel 文件路径（对于Excel类型）
        sheets: Optional[List[str]] - Excel 工作表列表（对于Excel类型）
        table_name: Optional[str] - 默认表名/工作表名
        host: Optional[str] - 数据库主机（对于数据库类型）
        port: Optional[int] - 数据库端口（对于数据库类型）
        database_name: Optional[str] - 数据库名（对于数据库类型）
    """
    connection_type: str
    connection_string: Optional[str] = None
    file_path: Optional[str] = None
    sheets: Optional[List[str]] = None
    table_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None


class DataSourceService:
    """数据源管理服务类"""

    def __init__(self):
        """初始化数据源服务"""
        self.encryption_service = encryption_service
        if not self.encryption_service:
            logger.warning("Encryption service not available")
        logger.info("Data source service initialized")

    async def create_data_source(
        self,
        tenant_id: str,
        name: str,
        connection_string: str,
        db: Session,
        db_type: str = "postgresql",
        host: Optional[str] = None,
        port: Optional[int] = None,
        database_name: Optional[str] = None
    ) -> DataSourceConnection:
        """
        创建新的数据源连接

        Args:
            tenant_id: 租户ID
            name: 数据源名称
            connection_string: 连接字符串（明文）
            db: 数据库会话（依赖注入）
            db_type: 数据库类型
            host: 主机地址
            port: 端口号
            database_name: 数据库名称

        Returns:
            创建的数据源连接对象
        """
        logger.info(f"Creating data source '{name}' for tenant '{tenant_id}'")

        # 验证租户是否存在
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' not found")

        # 检查名称是否已存在（在同一租户下）
        existing_connection = db.query(DataSourceConnection).filter(
            and_(
                DataSourceConnection.tenant_id == tenant_id,
                DataSourceConnection.name == name,
                DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
            )
        ).first()

        if existing_connection:
            raise ValueError(f"Data source name '{name}' already exists for this tenant")

        # 加密连接字符串
        encrypted_connection_string = self.encryption_service.encrypt_connection_string(connection_string)

        # 解析连接字符串获取连接信息（如果未提供）
        if not all([host, port, database_name]):
            parsed_info = self._parse_connection_string(connection_string, db_type)
            host = host or parsed_info.get("host")
            port = port or parsed_info.get("port")
            database_name = database_name or parsed_info.get("database")

        # 创建新的数据源连接
        new_connection = DataSourceConnection(
            tenant_id=tenant_id,
            name=name,
            connection_type=db_type,
            connection_string=encrypted_connection_string,
            host=host,
            port=port,
            database_name=database_name,
            status=DataSourceConnectionStatus.ACTIVE
        )

        # 使用依赖注入的数据库会话
        db.add(new_connection)
        db.commit()
        db.refresh(new_connection)

        logger.info(f"Data source '{name}' created successfully with ID {new_connection.id}")
        return new_connection

    async def get_data_sources(
        self,
        tenant_id: str,
        db: Session,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[DataSourceConnection]:
        """
        获取租户的所有数据源

        Args:
            tenant_id: 租户ID
            db: 数据库会话
            active_only: 是否只获取活跃的数据源
            skip: 跳过的记录数
            limit: 返回的记录数限制

        Returns:
            数据源连接列表
        """
        logger.info(f"Fetching data sources for tenant '{tenant_id}'")

        query = db.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id
        )

        if active_only:
            # 只获取ACTIVE状态的数据源
            query = query.filter(DataSourceConnection.status == DataSourceConnectionStatus.ACTIVE)
        else:
            # 即使选择"所有状态"，也要排除已软删除的INACTIVE状态
            query = query.filter(DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE)

        connections = query.order_by(
            DataSourceConnection.created_at.desc()
        ).offset(skip).limit(limit).all()

        logger.info(f"Found {len(connections)} data sources for tenant '{tenant_id}'")
        return connections

    async def get_data_source_by_id(
        self,
        data_source_id: str,
        tenant_id: str,
        db: Session
    ) -> Optional[DataSourceConnection]:
        """
        根据ID获取数据源连接（确保租户隔离）

        Args:
            data_source_id: 数据源ID
            tenant_id: 租户ID
            db: 数据库会话

        Returns:
            数据源连接对象或None
        """
        logger.info(f"Fetching data source {data_source_id} for tenant '{tenant_id}'")

        connection = db.query(DataSourceConnection).filter(
            and_(
                DataSourceConnection.id == data_source_id,
                DataSourceConnection.tenant_id == tenant_id
            )
        ).first()

        if connection:
            logger.info(f"Data source {data_source_id} found for tenant '{tenant_id}'")
        else:
            logger.warning(f"Data source {data_source_id} not found for tenant '{tenant_id}'")

        return connection

    async def update_data_source(
        self,
        data_source_id: str,
        tenant_id: str,
        update_data: Dict[str, Any],
        db: Session
    ) -> DataSourceConnection:
        """
        更新数据源连接

        Args:
            data_source_id: 数据源ID
            tenant_id: 租户ID
            update_data: 更新的数据
            db: 数据库会话

        Returns:
            更新后的数据源连接对象
        """
        logger.info(f"Updating data source {data_source_id} for tenant '{tenant_id}'")

        # 获取数据源（确保租户隔离）
        connection = await self.get_data_source_by_id(data_source_id, tenant_id, db)
        if not connection:
            raise ValueError(f"Data source {data_source_id} not found for tenant '{tenant_id}'")

        # 更新字段
        if "name" in update_data:
            # 检查新名称是否已存在（在同一租户下）
            existing_connection = db.query(DataSourceConnection).filter(
                and_(
                    DataSourceConnection.tenant_id == tenant_id,
                    DataSourceConnection.name == update_data["name"],
                    DataSourceConnection.id != data_source_id,
                    DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
                )
            ).first()

            if existing_connection:
                raise ValueError(f"Data source name '{update_data['name']}' already exists for this tenant")

            connection.name = update_data["name"]

        if "connection_string" in update_data:
            # 加密新的连接字符串
            encrypted_string = self.encryption_service.encrypt_connection_string(
                update_data["connection_string"]
            )
            connection.connection_string = encrypted_string

            # 解析新连接字符串更新连接信息
            parsed_info = self._parse_connection_string(
                update_data["connection_string"],
                connection.connection_type
            )
            connection.host = parsed_info.get("host")
            connection.port = parsed_info.get("port")
            connection.database_name = parsed_info.get("database")

        if "connection_type" in update_data:
            connection.connection_type = update_data["connection_type"]

        if "is_active" in update_data:
            if update_data["is_active"]:
                connection.status = DataSourceConnectionStatus.ACTIVE
            else:
                connection.status = DataSourceConnectionStatus.INACTIVE

        connection.updated_at = datetime.now()

        db.commit()
        db.refresh(connection)

        logger.info(f"Data source {data_source_id} updated successfully")
        return connection

    async def delete_data_source(
        self,
        data_source_id: str,
        tenant_id: str,
        db: Session
    ) -> bool:
        """
        删除数据源连接（软删除）

        Args:
            data_source_id: 数据源ID
            tenant_id: 租户ID
            db: 数据库会话

        Returns:
            是否删除成功
        """
        logger.info(f"Deleting data source {data_source_id} for tenant '{tenant_id}'")

        # 获取数据源（确保租户隔离）
        connection = await self.get_data_source_by_id(data_source_id, tenant_id, db)
        if not connection:
            raise ValueError(f"Data source {data_source_id} not found for tenant '{tenant_id}'")

        # 软删除：设置为非活跃状态
        connection.status = DataSourceConnectionStatus.INACTIVE
        connection.updated_at = datetime.now()

        db.commit()

        logger.info(f"Data source {data_source_id} deleted successfully (soft delete)")
        return True

    async def get_decrypted_connection_string(
        self,
        data_source_id: str,
        tenant_id: str,
        db: Session
    ) -> str:
        """
        获取解密后的连接字符串

        Args:
            data_source_id: 数据源ID
            tenant_id: 租户ID
            db: 数据库会话

        Returns:
            解密后的连接字符串
        """
        connection = await self.get_data_source_by_id(data_source_id, tenant_id, db)
        if not connection:
            raise ValueError(f"Data source {data_source_id} not found for tenant '{tenant_id}'")

        try:
            # connection.connection_string 属性已经会自动解密
            # 直接返回即可，不需要再次调用 decrypt_connection_string
            return connection.connection_string
        except Exception as e:
            logger.error(f"Failed to get connection string for data source {data_source_id}: {e}")
            raise RuntimeError("Failed to decrypt connection string")

    def _parse_connection_string(self, connection_string: str, db_type: str) -> Dict[str, Any]:
        """
        解析连接字符串获取连接信息

        Args:
            connection_string: 连接字符串
            db_type: 数据库类型

        Returns:
            解析后的连接信息
        """
        try:
            if db_type == "postgresql":
                return self._parse_postgresql_connection_string(connection_string)
            elif db_type == "mysql":
                return self._parse_mysql_connection_string(connection_string)
            else:
                logger.warning(f"Unsupported database type for parsing: {db_type}")
                return {}
        except Exception as e:
            logger.warning(f"Failed to parse connection string: {e}")
            return {}

    def _parse_postgresql_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """解析PostgreSQL连接字符串"""
        # 支持格式: postgresql://username:password@host:port/database 或 postgresql://username:password@host/database
        try:
            from urllib.parse import urlparse
            parsed = urlparse(connection_string)

            if parsed.scheme not in ['postgresql', 'postgres']:
                return {}

            result = {
                "username": parsed.username or "",
                "password": parsed.password or "",
                "host": parsed.hostname or "",
                "port": parsed.port or 5432,  # PostgreSQL 默认端口
                "database": parsed.path.lstrip('/') if parsed.path else ""
            }

            # 验证必需字段
            if not result["host"] or not result["database"]:
                return {}

            return result
        except Exception as e:
            logger.warning(f"Failed to parse PostgreSQL connection string: {e}")
            return {}

    def _parse_mysql_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """解析MySQL连接字符串"""
        # 支持格式: mysql://username:password@host:port/database 或 mysql://username:password@host/database
        try:
            from urllib.parse import urlparse
            parsed = urlparse(connection_string)

            if parsed.scheme != 'mysql':
                return {}

            result = {
                "username": parsed.username or "",
                "password": parsed.password or "",
                "host": parsed.hostname or "",
                "port": parsed.port or 3306,  # MySQL 默认端口
                "database": parsed.path.lstrip('/') if parsed.path else ""
            }

            # 验证必需字段
            if not result["host"] or not result["database"]:
                return {}

            return result
        except Exception as e:
            logger.warning(f"Failed to parse MySQL connection string: {e}")
            return {}

    async def get_data_source_connection_info(
        self,
        connection_id: str,
        tenant_id: str,
        db: Session
    ) -> DataSourceConnectionInfo:
        """
        获取数据源连接信息（用于AgentV2查询）

        根据数据源类型返回不同的连接信息：
        - Excel: 返回文件路径、工作表列表
        - PostgreSQL/MySQL: 返回解密后的连接字符串

        Args:
            connection_id: 数据源连接ID
            tenant_id: 租户ID
            db: 数据库会话

        Returns:
            DataSourceConnectionInfo: 数据源连接信息对象

        Raises:
            ValueError: 数据源不存在或无权访问
        """
        logger.info(f"Getting connection info for {connection_id}, tenant '{tenant_id}'")

        # 获取数据源
        connection = await self.get_data_source_by_id(connection_id, tenant_id, db)
        if not connection:
            raise ValueError(f"Data source {connection_id} not found for tenant '{tenant_id}'")

        db_type = connection.db_type.lower()
        logger.info(f"Data source type: {db_type}")

        # 处理 Excel 文件类型
        if db_type in ["xlsx", "xls", "excel"]:
            return await self._get_excel_connection_info(connection)

        # 处理数据库类型
        elif db_type in ["postgresql", "mysql", "sqlite"]:
            return self._get_database_connection_info(connection)

        else:
            # 默认按数据库处理
            logger.warning(f"Unknown data source type '{db_type}', treating as database")
            return self._get_database_connection_info(connection)

    async def _get_excel_connection_info(
        self,
        connection: DataSourceConnection
    ) -> DataSourceConnectionInfo:
        """
        获取Excel文件的连接信息

        Args:
            connection: 数据源连接对象

        Returns:
            DataSourceConnectionInfo: Excel连接信息
        """
        try:
            import pandas as pd

            # 获取文件路径
            # connection_string 存储的是 MinIO 路径或本地路径
            file_path = connection.connection_string

            # 如果是 MinIO 路径，需要下载到本地
            if file_path.startswith("minio://") or file_path.startswith("file://"):
                # 从 MinIO 下载文件
                from .minio_client import minio_service

                # 去掉协议前缀
                if file_path.startswith("minio://"):
                    storage_path = file_path[8:]  # 去掉 "minio://"
                else:
                    storage_path = file_path[7:]  # 去掉 "file://"

                # 下载文件到临时目录
                import tempfile
                temp_dir = tempfile.gettempdir()
                local_filename = os.path.basename(storage_path)
                local_path = os.path.join(temp_dir, local_filename)

                # 从 MinIO 下载
                bucket_name = "data-sources"
                file_data = minio_service.download_file(
                    bucket_name=bucket_name,
                    object_name=storage_path
                )

                if file_data:
                    with open(local_path, 'wb') as f:
                        f.write(file_data)
                    file_path = local_path
                else:
                    raise FileNotFoundError(f"File not found in MinIO: {storage_path}")

            # 验证文件存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Excel file not found: {file_path}")

            # 读取 Excel 工作表列表
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
            sheet_names = excel_file.sheet_names

            logger.info(f"Excel file loaded: {file_path}, sheets: {sheet_names}")

            return DataSourceConnectionInfo(
                connection_type="excel",
                file_path=file_path,
                sheets=sheet_names,
                table_name=sheet_names[0] if sheet_names else None,  # 默认第一个工作表
                database_name=connection.database_name  # 原始文件名
            )

        except FileNotFoundError as e:
            logger.error(f"Excel file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
            raise RuntimeError(f"Failed to load Excel file: {str(e)}")

    def _get_database_connection_info(
        self,
        connection: DataSourceConnection
    ) -> DataSourceConnectionInfo:
        """
        获取数据库的连接信息

        Args:
            connection: 数据源连接对象

        Returns:
            DataSourceConnectionInfo: 数据库连接信息
        """
        # connection.connection_string 属性会自动解密
        connection_string = connection.connection_string

        return DataSourceConnectionInfo(
            connection_type=connection.db_type,
            connection_string=connection_string,
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name
        )


# 全局数据源服务实例
data_source_service = DataSourceService()