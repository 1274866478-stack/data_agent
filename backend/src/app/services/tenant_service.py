"""
# [TENANT_SERVICE] 租户管理服务

## [HEADER]
**文件名**: tenant_service.py
**职责**: 实现租户CRUD操作、租户初始化、统计信息查询、状态管理和软删除功能（Story-2.2）
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 租户管理服务（Story-2.2要求）

## [INPUT]
- **tenant_id: str** - 租户唯一标识符
- **email: str** - 租户邮箱地址
- **display_name: Optional[str]** - 租户显示名称
- **settings: Optional[Dict[str, Any]]** - 租户特定设置
- **update_data: Dict[str, Any]** - 更新数据字典
- **status: TenantStatus** - 租户状态枚举（ACTIVE, SUSPENDED, DELETED）
- **db: Session** - SQLAlchemy数据库会话（依赖注入）

## [OUTPUT]
- **Tenant**: 租户对象（create_tenant, get_tenant_by_id, get_tenant_by_email, update_tenant）
- **bool**: 操作成功/失败（delete_tenant, suspend_tenant, activate_tenant）
- **Optional[Dict[str, Any]]**: 租户统计信息（get_tenant_stats）
  - total_documents: int - 总文档数
  - total_data_sources: int - 数据源连接数
  - storage_used_mb: int - 已用存储（MB）
  - processed_documents: int - 已处理文档数
  - pending_documents: int - 待处理文档数
  - storage_quota_mb: int - 存储配额（MB）
  - storage_usage_percent: float - 存储使用百分比
- **Dict[str, Any]**: 初始化结果（setup_new_tenant）
  - success: bool - 是否成功
  - tenant_id: str - 租户ID
  - message: str - 结果消息
  - tenant: Dict - 租户对象字典

**上游依赖** (已读取源码):
- [./data/models.py](./data/models.py) - 数据模型（Tenant, TenantStatus, DataSourceConnection, KnowledgeDocument）
- [./data/database.py](./data/database.py) - 数据库连接（get_db）

**下游依赖** (需要反向索引分析):
- [../api/v1/endpoints/tenants.py](../api/v1/endpoints/tenants.py) - 租户API端点
- [../api/v1/endpoints/auth.py](../api/v1/endpoints/auth.py) - 认证端点（租户创建）

**调用方**:
- 租户注册流程
- 租户管理API
- 租户统计查询
- 租户状态管理

## [STATE]
- **数据库会话**: 通过__init__注入，所有操作使用self.db
- **依赖注入**: get_tenant_service和get_tenant_setup_service函数使用FastAPI的Depends
- **复合查询**: 统计信息需要关联查询DataSourceConnection和KnowledgeDocument
- **软删除策略**: 使用status=DELETED标记，不物理删除数据
- **设置合并**: update_tenant中settings采用合并策略而非完全替换
- **存储计算**: storage_used_mb通过sum(file_size)聚合计算

## [SIDE-EFFECTS]
- **数据库事务**: commit操作持久化变更（create, update, delete, suspend, activate）
- **刷新操作**: refresh操作获取最新数据（create, update后）
- **查询过滤**: get操作自动过滤status=DELETED的租户
- **统计聚合**: sum()和count()聚合查询（可能影响性能）
- **异常抛出**: duplicate tenant/email时抛出ValueError
- **时间戳更新**: 所有修改操作自动更新updated_at字段

## [POS]
**路径**: backend/src/app/services/tenant_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 data.models 和 data.database
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import Depends

from src.app.data.models import Tenant, TenantStatus, DataSourceConnection, KnowledgeDocument, DataSourceConnectionStatus
from src.app.data.database import get_db


class TenantService:
    """租户管理服务（Story-2.2要求）"""

    def __init__(self, db: Session):
        self.db = db

    async def create_tenant(
        self,
        tenant_id: str,
        email: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        创建新租户（Story要求）

        Args:
            tenant_id: 租户唯一标识符
            email: 租户邮箱
            settings: 租户特定设置

        Returns:
            Tenant: 创建的租户对象
        """
        # 检查租户是否已存在
        existing_tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if existing_tenant:
            raise ValueError(f"Tenant with ID {tenant_id} already exists")

        # 检查邮箱是否已存在
        existing_email = self.db.query(Tenant).filter(Tenant.email == email).first()
        if existing_email:
            raise ValueError(f"Email {email} is already registered")

        # 创建新租户
        new_tenant = Tenant(
            id=tenant_id,
            email=email,
            status=TenantStatus.ACTIVE,
            settings=settings or {}
        )

        self.db.add(new_tenant)
        self.db.commit()
        self.db.refresh(new_tenant)

        return new_tenant

    async def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """
        根据ID获取租户（Story要求）

        Args:
            tenant_id: 租户ID

        Returns:
            Optional[Tenant]: 租户对象或None
        """
        return self.db.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.status != TenantStatus.DELETED
        ).first()

    async def get_tenant_by_email(self, email: str) -> Optional[Tenant]:
        """
        根据邮箱获取租户

        Args:
            email: 租户邮箱

        Returns:
            Optional[Tenant]: 租户对象或None
        """
        return self.db.query(Tenant).filter(
            Tenant.email == email,
            Tenant.status != TenantStatus.DELETED
        ).first()

    async def update_tenant(
        self,
        tenant_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Tenant]:
        """
        更新租户信息（Story要求）

        Args:
            tenant_id: 租户ID
            update_data: 更新数据

        Returns:
            Optional[Tenant]: 更新后的租户对象或None
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # 更新允许的字段
        if "display_name" in update_data:
            tenant.display_name = update_data["display_name"]

        if "settings" in update_data:
            # 合并设置，不是完全替换
            current_settings = tenant.settings or {}
            current_settings.update(update_data["settings"])
            tenant.settings = current_settings

        if "storage_quota_mb" in update_data:
            tenant.storage_quota_mb = update_data["storage_quota_mb"]

        if "status" in update_data:
            # 验证状态值
            try:
                tenant.status = TenantStatus(update_data["status"])
            except ValueError:
                raise ValueError(f"Invalid status: {update_data['status']}")

        tenant.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    async def delete_tenant(self, tenant_id: str) -> bool:
        """
        软删除租户（Story要求）

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 删除是否成功
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False

        # 软删除：设置为已删除状态
        tenant.status = TenantStatus.DELETED
        tenant.updated_at = datetime.now()

        self.db.commit()
        return True

    async def suspend_tenant(self, tenant_id: str) -> bool:
        """
        暂停租户

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 暂停是否成功
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.now()

        self.db.commit()
        return True

    async def activate_tenant(self, tenant_id: str) -> bool:
        """
        激活租户

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 激活是否成功
        """
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.now()

        self.db.commit()
        return True

    async def get_tenant_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取租户统计信息（Story要求）

        Args:
            tenant_id: 租户ID

        Returns:
            Optional[Dict[str, Any]]: 统计信息或None
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        # 统计数据源连接数
        data_source_count = self.db.query(DataSourceConnection).filter(
            DataSourceConnection.tenant_id == tenant_id,
            DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE
        ).count()

        # 统计文档数量
        total_documents = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_id
        ).count()

        # 统计已处理文档数量
        processed_documents = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.processing_status == "completed"
        ).count()

        # 计算存储使用量（这里简化计算，实际应该从MinIO获取）
        storage_used_mb = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_id
        ).with_entities(
            self.db.func.sum(KnowledgeDocument.file_size)
        ).scalar() or 0

        storage_used_mb = storage_used_mb // (1024 * 1024)  # 转换为MB

        return {
            "total_documents": total_documents,
            "total_data_sources": data_source_count,
            "storage_used_mb": storage_used_mb,
            "processed_documents": processed_documents,
            "pending_documents": total_documents - processed_documents,
            "storage_quota_mb": tenant.storage_quota_mb,
            "storage_usage_percent": min(100, (storage_used_mb / tenant.storage_quota_mb) * 100) if tenant.storage_quota_mb > 0 else 0
        }


class TenantSetupService:
    """租户初始化服务（Story要求的/setup端点支持）"""

    def __init__(self, db: Session):
        self.db = db
        self.tenant_service = TenantService(db)

    async def setup_new_tenant(
        self,
        tenant_id: str,
        email: str,
        display_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        新租户初始化（Story要求）

        Args:
            tenant_id: 租户ID
            email: 租户邮箱
            display_name: 显示名称
            settings: 初始设置

        Returns:
            Dict[str, Any]: 初始化结果
        """
        try:
            # 创建租户
            tenant = await self.tenant_service.create_tenant(
                tenant_id=tenant_id,
                email=email,
                settings=settings
            )

            # 设置显示名称
            if display_name:
                await self.tenant_service.update_tenant(
                    tenant_id=tenant_id,
                    update_data={"display_name": display_name}
                )

            return {
                "success": True,
                "tenant_id": tenant.id,
                "message": "Tenant setup completed successfully",
                "tenant": tenant.to_dict()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Tenant setup failed"
            }


# 依赖注入函数
def get_tenant_service(db: Session = Depends(get_db)) -> TenantService:
    """获取租户服务实例"""
    return TenantService(db)


def get_tenant_setup_service(db: Session = Depends(get_db)) -> TenantSetupService:
    """获取租户初始化服务实例"""
    return TenantSetupService(db)