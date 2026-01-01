"""
# [TENANTS] 租户管理API端点

## [HEADER]
**文件名**: tenants.py
**职责**: 实现多租户SaaS架构的租户管理API，支持租户查询、更新、统计和初始化
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现租户管理端点

## [INPUT]
- **tenant_id: str** - 租户ID（从JWT token中提取）
- **current_tenant: Tenant** - 当前租户对象（通过依赖注入获取）
- **update_data: TenantUpdateRequest** - 租户更新请求数据（Pydantic模型）
- **setup_data: TenantSetupRequest** - 租户初始化请求数据（Pydantic模型）
- **db: Session** - 数据库会话（通过依赖注入获取）

## [OUTPUT]
- **tenant_info: dict** - 租户信息字典
  - id: 租户ID
  - email: 租户邮箱
  - status: 租户状态
  - display_name: 显示名称
  - settings: 租户设置
  - storage_quota_mb: 存储配额
- **tenant_stats: dict** - 租户统计信息
  - data_sources_count: 数据源数量
  - documents_count: 文档数量
  - storage_used_mb: 已用存储
- **error_response: HTTPException** - 错误响应（400, 404, 500）

## [LINK]
**上游依赖** (已读取源码):
- [../../data/database.py](../../data/database.py) - get_db(), Session
- [../../data/models.py](../../data/models.py) - Tenant模型
- [../../services/tenant_service.py](../../services/tenant_service.py) - 租户服务层
- [../../middleware/tenant_context.py](../../middleware/tenant_context.py) - 租户上下文（get_current_tenant, get_current_tenant_id）

**下游依赖** (已读取源码):
- 无（API端点是叶子模块）

**调用方**:
- 前端租户管理页面 - 调用租户管理API
- 前端仪表板 - 显示租户信息和统计
- 租户初始化流程 - 创建新租户

## [POS]
**路径**: backend/src/app/api/v1/endpoints/tenants.py
**模块层级**: Level 3 - API端点层
**依赖深度**: 直接依赖 data/*, services/*, middleware/*；被前端租户管理模块调用
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime

from src.app.data.database import get_db
from src.app.data.models import Tenant
from src.app.services.tenant_service import get_tenant_service, get_tenant_setup_service, TenantService, TenantSetupService
from src.app.middleware.tenant_context import get_current_tenant, get_current_tenant_id

router = APIRouter()


# Pydantic模型用于请求验证
class TenantUpdateRequest(BaseModel):
    """租户更新请求模型"""
    display_name: str = None
    settings: Dict[str, Any] = None
    storage_quota_mb: int = None


class TenantSetupRequest(BaseModel):
    """租户初始化请求模型"""
    tenant_id: str
    email: str
    display_name: str = None
    settings: Dict[str, Any] = None


@router.get("/me", summary="获取当前租户信息")
async def get_current_tenant(
    current_tenant: Tenant = Depends(get_current_tenant)
) -> Dict[str, Any]:
    """
    获取当前租户信息（Story要求：GET /api/v1/tenants/me）
    """
    try:
        return current_tenant.to_dict()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant info: {str(e)}"
        )


@router.put("/me", summary="更新当前租户信息")
async def update_current_tenant(
    update_data: TenantUpdateRequest,
    tenant_service: TenantService = Depends(get_tenant_service),
    tenant_id: str = Depends(get_current_tenant_id)
) -> Dict[str, Any]:
    """
    更新当前租户信息（Story要求：PUT /api/v1/tenants/me）
    """
    try:
        # 只传递非None字段
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

        tenant = await tenant_service.update_tenant(tenant_id, update_dict)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        return tenant.to_dict()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.get("/me/stats", summary="获取租户统计信息")
async def get_current_tenant_stats(
    tenant_service: TenantService = Depends(get_tenant_service),
    tenant_id: str = Depends(get_current_tenant_id)
) -> Dict[str, Any]:
    """
    获取租户统计信息（Story要求：GET /api/v1/tenants/me/stats）
    """
    try:
        stats = await tenant_service.get_tenant_stats(tenant_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        return {
            "tenant_id": tenant_id,
            "statistics": stats,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant stats: {str(e)}"
        )


@router.post("/setup", summary="新租户初始化", status_code=status.HTTP_201_CREATED)
async def setup_tenant(
    setup_data: TenantSetupRequest,
    tenant_setup_service: TenantSetupService = Depends(get_tenant_setup_service)
) -> Dict[str, Any]:
    """
    新租户初始化（Story要求：POST /api/v1/tenants/setup）
    """
    try:
        result = await tenant_setup_service.setup_new_tenant(
            tenant_id=setup_data.tenant_id,
            email=setup_data.email,
            display_name=setup_data.display_name,
            settings=setup_data.settings
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Tenant setup failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup tenant: {str(e)}"
        )


# 保留一些管理端点（用于管理员）
@router.get("/", summary="获取所有租户（管理员）")
async def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取所有租户列表（管理员功能）
    """
    try:
        from src.app.data.models import Tenant, TenantStatus

        query = db.query(Tenant).filter(Tenant.status != TenantStatus.DELETED)
        total = query.count()

        tenants = query.offset(skip).limit(limit).all()

        return {
            "tenants": [tenant.to_dict() for tenant in tenants],
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenants: {str(e)}"
        )


@router.get("/{tenant_id}/admin", summary="获取租户详情（管理员）")
async def get_tenant_admin(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service)
) -> Dict[str, Any]:
    """
    获取租户详情（管理员功能，包括已删除的租户）
    """
    try:
        # 直接查询，不过滤已删除状态
        from src.app.data.models import Tenant
        from src.app.data.database import get_db

        db = next(get_db())
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        return tenant.to_dict()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {str(e)}"
        )