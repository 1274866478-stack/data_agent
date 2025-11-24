"""
数据源管理服务
处理数据源的CRUD操作和租户隔离
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

try:
    from ..data.models import DataSourceConnection, Tenant
except ImportError as e:
    logging.error(f"Failed to import models: {e}")
    DataSourceConnection = None
    Tenant = None

try:
    from .encryption_service import encryption_service
except ImportError as e:
    logging.error(f"Failed to import encryption service: {e}")
    encryption_service = None

logger = logging.getLogger(__name__)


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
                DataSourceConnection.is_active == True
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
            is_active=True
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
            query = query.filter(DataSourceConnection.is_active == True)

        connections = query.order_by(
            DataSourceConnection.created_at.desc()
        ).offset(skip).limit(limit).all()

        logger.info(f"Found {len(connections)} data sources for tenant '{tenant_id}'")
        return connections

    async def get_data_source_by_id(
        self,
        data_source_id: int,
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
        data_source_id: int,
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
                    DataSourceConnection.is_active == True
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
            connection.is_active = update_data["is_active"]

        connection.updated_at = datetime.now()

        db.commit()
        db.refresh(connection)

        logger.info(f"Data source {data_source_id} updated successfully")
        return connection

    async def delete_data_source(
        self,
        data_source_id: int,
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
        connection.is_active = False
        connection.updated_at = datetime.now()

        db.commit()

        logger.info(f"Data source {data_source_id} deleted successfully (soft delete)")
        return True

    async def get_decrypted_connection_string(
        self,
        data_source_id: int,
        tenant_id: str,
        db: Session
    ) -> str:
        """
        获取解密后的连接字符串（临时使用）

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
            return self.encryption_service.decrypt_connection_string(connection.connection_string)
        except Exception as e:
            logger.error(f"Failed to decrypt connection string for data source {data_source_id}: {e}")
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
        # 示例: postgresql://username:password@host:port/database
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
            return {}
        except Exception:
            return {}

    def _parse_mysql_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """解析MySQL连接字符串"""
        # 示例: mysql://username:password@host:port/database
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
            return {}
        except Exception:
            return {}


# 全局数据源服务实例
data_source_service = DataSourceService()