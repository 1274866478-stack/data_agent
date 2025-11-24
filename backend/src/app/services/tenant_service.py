"""
租户服务模块
实现Story-2.2要求的租户业务逻辑
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import Depends

from src.app.data.models import Tenant, TenantStatus, DataSourceConnection, KnowledgeDocument
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
            DataSourceConnection.is_active == True
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