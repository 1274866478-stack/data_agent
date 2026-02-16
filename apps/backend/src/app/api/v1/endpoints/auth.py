"""
# [AUTH] 认证API端点

## [HEADER]
**文件名**: auth.py
**职责**: 提供用户认证、JWT验证、租户管理和用户信息管理功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 认证端点实现

## [INPUT]
### HTTP请求
- **POST /auth/verify**: Token验证请求 - TokenVerifyRequest {token: str}
- **GET /auth/me**: 获取当前用户 - 需要有效JWT Token
- **GET /auth/tenant**: 获取租户信息 - 需要有效JWT Token
- **POST /auth/refresh-tenant**: 刷新租户信息 - 需要有效JWT Token
- **GET /auth/status**: 获取认证状态 - 可选认证
- **POST /auth/logout**: 用户登出 - 需要有效JWT Token
- **GET /auth/config**: 获取认证配置 - 无需认证
- **POST /auth/test-token**: 测试Token验证 - 可选认证 {token: str}

### 依赖注入
- **get_current_user_with_tenant**: 从JWT Token提取当前用户和租户信息
- **get_current_user_optional**: 可选的用户认证依赖
- **get_db**: SQLAlchemy数据库会话

## [OUTPUT]
### API响应
- **TokenVerifyResponse**: Token验证结果 - {valid, user_info, expires_at, error_message}
- **UserInfoResponse**: 用户信息 - {user_id, tenant_id, email, first_name, last_name, is_verified, created_at}
- **TenantInfoResponse**: 租户信息 - {tenant_id, email, created_at, status}
- **认证配置**: {auth_provider, jwt_issuer, supported_flows, token_validation, tenant_isolation}

### 核心功能
- **JWT Token验证**: 验证Clerk JWT Token有效性并提取用户信息
- **租户自动创建**: 当租户不存在时自动创建租户记录
- **用户信息获取**: 从Token中提取用户详细信息
- **认证状态检查**: 检查当前请求的认证状态
- **登出处理**: 记录登出事件(无状态JWT系统)

## [LINK]
**上游依赖** (已读取源码):
- [../../core/auth.py](../../core/auth.py) - 认证中间件(get_current_user_with_tenant, get_current_user_optional)
- [../../core/jwt_utils.py](../../core/jwt_utils.py) - JWT工具(validate_clerk_token, get_token_expiration, create_tenant_for_user)
- [../../data/models.py](../../data/models.py) - 数据模型(Tenant)
- [../../data/database.py](../../data/database.py) - 数据库连接(get_db)

**下游依赖**:
- **前端应用**: 通过/api/v1/auth/*端点进行认证操作
- **API文档**: FastAPI自动生成OpenAPI文档

**调用方**:
- **前端Clerk集成**: 验证Token并获取用户信息
- **租户管理**: 自动创建和刷新租户记录
- **API测试**: 使用test-token端点调试认证

## [POS]
**路径**: backend/src/app/api/v1/endpoints/auth.py
**模块层级**: Level 5 (Backend → src/app → api/v1 → endpoints → auth)
**依赖深度**: 2层 (core和data模块)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from src.app.core.auth import get_current_user_with_tenant, get_current_user_optional
from src.app.core.jwt_utils import validate_clerk_token, JWTValidationError, get_token_expiration
from src.app.data.models import Tenant
from src.app.data.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenVerifyRequest(BaseModel):
    """Token验证请求模型"""
    token: str


class TokenVerifyResponse(BaseModel):
    """Token验证响应模型"""
    valid: bool
    user_info: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    error_message: Optional[str] = None


class UserInfoResponse(BaseModel):
    """用户信息响应模型"""
    user_id: str
    tenant_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False
    created_at: Optional[str] = None


class TenantInfoResponse(BaseModel):
    """租户信息响应模型"""
    tenant_id: str
    email: Optional[str] = None
    created_at: str
    status: str


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(request: TokenVerifyRequest):
    """
    验证JWT Token有效性
    不需要认证，用于前端验证token
    """
    try:
        # 验证token并获取用户信息
        user_info = await validate_clerk_token(request.token)

        # 获取token过期时间
        expires_at = get_token_expiration(request.token)
        expires_at_str = expires_at.isoformat() if expires_at else None

        return TokenVerifyResponse(
            valid=True,
            user_info=user_info,
            expires_at=expires_at_str
        )

    except JWTValidationError as e:
        logger.warning(f"Token verification failed: {e}")
        return TokenVerifyResponse(
            valid=False,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return TokenVerifyResponse(
            valid=False,
            error_message="Internal server error during verification"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user(
    current_user = Depends(get_current_user_with_tenant)
):
    """
    获取当前用户信息
    需要有效的JWT Token
    """
    try:
        return UserInfoResponse(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            email=getattr(current_user, 'email', None),
            first_name=getattr(current_user, 'first_name', None),
            last_name=getattr(current_user, 'last_name', None),
            is_verified=getattr(current_user, 'is_verified', False),
            created_at=getattr(current_user, 'created_at', None)
        )

    except Exception as e:
        logger.error(f"Get current user info failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.get("/tenant", response_model=TenantInfoResponse)
async def get_tenant_info(
    current_user = Depends(get_current_user_with_tenant),
    db: Session = Depends(get_db)
):
    """
    获取当前用户租户信息
    需要有效的JWT Token
    """
    try:
        tenant_id = current_user.tenant_id

        # 从数据库获取租户信息
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if tenant:
            return TenantInfoResponse(
                tenant_id=tenant.id,
                email=tenant.email,
                created_at=tenant.created_at.isoformat(),
                status="active"
            )
        else:
            # 租户不存在，创建新租户
            from src.app.core.jwt_utils import create_tenant_for_user

            user_info = {
                'tenant_id': tenant_id,
                'email': getattr(current_user, 'email', None)
            }

            await create_tenant_for_user(user_info)

            return TenantInfoResponse(
                tenant_id=tenant_id,
                email=getattr(current_user, 'email', None),
                created_at=datetime.utcnow().isoformat(),
                status="created"
            )

    except Exception as e:
        logger.error(f"Get tenant info failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant information"
        )


@router.post("/refresh-tenant")
async def refresh_tenant(
    current_user = Depends(get_current_user_with_tenant),
    db: Session = Depends(get_db)
):
    """
    刷新/创建租户信息
    用于确保租户记录存在
    """
    try:
        tenant_id = current_user.tenant_id

        # 检查租户是否存在
        existing_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not existing_tenant:
            # 创建新租户
            new_tenant = Tenant(
                id=tenant_id,
                email=getattr(current_user, 'email', None),
                created_at=datetime.utcnow()
            )
            db.add(new_tenant)
            db.commit()
            db.refresh(new_tenant)

            logger.info(f"Created tenant for user {current_user.id}: {tenant_id}")

            return {
                "message": "Tenant created successfully",
                "tenant_id": tenant_id,
                "status": "created"
            }
        else:
            # 更新租户信息
            if current_user.email and existing_tenant.email != current_user.email:
                existing_tenant.email = current_user.email
                db.commit()

            return {
                "message": "Tenant already exists",
                "tenant_id": tenant_id,
                "status": "existing"
            }

    except Exception as e:
        logger.error(f"Refresh tenant failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh tenant information"
        )


@router.get("/status")
async def get_auth_status(
    current_user = Depends(get_current_user_optional)
):
    """
    获取认证状态
    可选认证，返回当前用户的认证状态
    """
    if current_user is None:
        return {
            "authenticated": False,
            "user": None,
            "message": "No valid authentication provided"
        }

    return {
        "authenticated": True,
        "user": {
            "user_id": current_user.get('user_id'),
            "tenant_id": current_user.get('tenant_id'),
            "email": current_user.get('email'),
            "is_verified": current_user.get('is_verified', False)
        },
        "message": "User is authenticated"
    }


@router.post("/logout")
async def logout(
    current_user = Depends(get_current_user_with_tenant)
):
    """
    用户登出
    在无状态JWT系统中，主要是客户端清除token
    """
    try:
        # 记录登出事件
        logger.info(f"User {current_user.id} logged out")

        # 在实际应用中，可以在这里：
        # 1. 将token加入黑名单（如果使用token黑名单机制）
        # 2. 清除用户会话缓存
        # 3. 记录登出事件到审计日志

        return {
            "message": "Logout successful",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/config")
async def get_auth_config():
    """
    获取认证配置信息
    用于前端了解认证设置
    """
    try:
        from src.app.core.config import settings

        config = {
            "auth_provider": "clerk",
            "jwt_issuer": f"https://clerk.{getattr(settings, 'clerk_domain', 'clerk.accounts.dev')}",
            "supported_flows": ["jwt", "api_key"],
            "token_validation": "enabled",
            "tenant_isolation": "enabled"
        }

        # 在开发环境中可以暴露更多信息
        if hasattr(settings, 'debug') and settings.debug:
            config.update({
                "clerk_domain": getattr(settings, 'clerk_domain', 'clerk.accounts.dev'),
                "api_key_auth_enabled": bool(getattr(settings, 'api_key', None))
            })

        return config

    except Exception as e:
        logger.error(f"Get auth config failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication configuration"
        )


@router.post("/test-token")
async def test_token_validation(
    token: str,
    current_user = Depends(get_current_user_optional)
):
    """
    测试Token验证功能
    用于调试和测试
    """
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required"
            )

        # 验证token
        user_info = await validate_clerk_token(token)
        expires_at = get_token_expiration(token)

        return {
            "valid": True,
            "user_info": user_info,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "validation_time": datetime.utcnow().isoformat()
        }

    except JWTValidationError as e:
        return {
            "valid": False,
            "error_message": str(e),
            "validation_time": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Test token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation test failed"
        )