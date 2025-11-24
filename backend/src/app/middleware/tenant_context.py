"""
租户上下文中间件
实现Story-2.2要求的从JWT提取tenant_id和租户隔离
线程安全版本 - 防止并发请求时的上下文污染
"""

from typing import Optional
import threading
from contextvars import ContextVar
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import structlog

from src.app.data.database import get_db
from src.app.data.models import Tenant, TenantStatus
from src.app.core.config import get_settings

logger = structlog.get_logger(__name__)
security = HTTPBearer()
settings = get_settings()

# 使用contextvars实现线程安全的上下文管理
# contextvars在Python 3.7+中是线程安全的，并且能在asyncio中正确工作
_current_tenant_id: ContextVar[Optional[str]] = ContextVar('_current_tenant_id', default=None)
_current_tenant: ContextVar[Optional[Tenant]] = ContextVar('_current_tenant', default=None)
_request_id: ContextVar[Optional[str]] = ContextVar('_request_id', default=None)


class TenantContext:
    """
    线程安全的租户上下文管理器

    使用contextvars确保每个请求都有独立的上下文，
    避免并发请求之间的数据污染
    """

    def __init__(self):
        """初始化租户上下文管理器"""
        self._lock = threading.RLock()  # 可重入锁用于额外的线程安全

    def set_tenant(self, tenant_id: str, tenant: Tenant = None, request_id: str = None):
        """
        设置当前租户上下文

        Args:
            tenant_id: 租户ID
            tenant: 租户对象（可选）
            request_id: 请求ID用于调试
        """
        with self._lock:
            _current_tenant_id.set(tenant_id)
            _current_tenant.set(tenant)
            if request_id:
                _request_id.set(request_id)

            logger.debug(
                "Tenant context set",
                tenant_id=tenant_id,
                request_id=request_id,
                thread_id=threading.get_ident()
            )

    def get_tenant_id(self) -> Optional[str]:
        """
        获取当前租户ID

        Returns:
            Optional[str]: 当前租户ID
        """
        with self._lock:
            tenant_id = _current_tenant_id.get()
            logger.debug(
                "Retrieved tenant ID",
                tenant_id=tenant_id,
                thread_id=threading.get_ident()
            )
            return tenant_id

    def get_tenant(self) -> Optional[Tenant]:
        """
        获取当前租户对象

        Returns:
            Optional[Tenant]: 当前租户对象
        """
        with self._lock:
            return _current_tenant.get()

    def get_request_id(self) -> Optional[str]:
        """
        获取当前请求ID

        Returns:
            Optional[str]: 请求ID
        """
        with self._lock:
            return _request_id.get()

    def clear(self):
        """清除当前租户上下文"""
        with self._lock:
            request_id = _request_id.get()
            tenant_id = _current_tenant_id.get()

            _current_tenant_id.set(None)
            _current_tenant.set(None)
            _request_id.set(None)

            logger.debug(
                "Tenant context cleared",
                previous_tenant_id=tenant_id,
                request_id=request_id,
                thread_id=threading.get_ident()
            )

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 自动清理上下文"""
        self.clear()


# 全局租户上下文实例（线程安全）
tenant_context = TenantContext()


# 请求级别的上下文管理器装饰器
def with_tenant_context(tenant_id: str, tenant: Tenant = None, request_id: str = None):
    """
    装饰器：为函数提供租户上下文

    Args:
        tenant_id: 租户ID
        tenant: 租户对象（可选）
        request_id: 请求ID（可选）

    Usage:
        @with_tenant_context("tenant_123")
        async def some_function():
            # 函数内部可以安全访问租户上下文
            tenant_id = tenant_context.get_tenant_id()
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with tenant_context:
                tenant_context.set_tenant(tenant_id, tenant, request_id)
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with tenant_context:
                tenant_context.set_tenant(tenant_id, tenant, request_id)
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def extract_tenant_from_jwt(token: str) -> Optional[str]:
    """
    从JWT token中提取tenant_id

    Args:
        token: JWT token

    Returns:
        Optional[str]: tenant_id或None
    """
    try:
        # 解码JWT token
        payload = jwt.decode(
            token,
            settings.CLERK_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )

        # 从Clerk JWT中提取用户ID作为tenant_id
        tenant_id = payload.get("sub")
        if not tenant_id:
            logger.warning("JWT token missing 'sub' claim")
            return None

        return tenant_id

    except JWTError as e:
        logger.warning(f"Failed to decode JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}")
        return None


async def get_current_tenant_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    从请求中提取并验证当前租户（线程安全版本）

    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭证
        db: 数据库会话

    Returns:
        Tenant: 当前租户对象

    Raises:
        HTTPException: 认证失败或租户不存在
    """
    # 生成请求ID用于调试和追踪
    import uuid
    request_id = str(uuid.uuid4())

    try:
        # 提取tenant_id
        tenant_id = extract_tenant_from_jwt(credentials.credentials)
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 查询租户
        tenant = db.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.status != TenantStatus.DELETED
        ).first()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # 检查租户状态
        if tenant.status == TenantStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is suspended"
            )

        # 设置线程安全的租户上下文
        tenant_context.set_tenant(tenant_id, tenant, request_id)

        # 记录访问日志（包含请求ID和线程ID用于调试）
        logger.info(
            "Tenant access",
            tenant_id=tenant_id,
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            thread_id=threading.get_ident(),
            user_agent=request.headers.get("User-Agent"),
            remote_address=request.client.host if request.client else None
        )

        return tenant

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "Error in get_current_tenant_from_request",
            request_id=request_id,
            error=str(e),
            thread_id=threading.get_ident()
        )
        # 确保上下文被清理
        tenant_context.clear()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during tenant authentication"
        )


def get_current_tenant_id() -> Optional[str]:
    """
    获取当前租户ID（用于在服务层使用）

    Returns:
        Optional[str]: 当前租户ID
    """
    return tenant_context.get_tenant_id()


def get_current_tenant() -> Optional[Tenant]:
    """
    获取当前租户对象（用于在服务层使用）

    Returns:
        Optional[Tenant]: 当前租户对象
    """
    return tenant_context.get_tenant()


# 依赖注入函数
async def get_tenant_from_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    从JWT token中获取tenant_id的依赖注入函数

    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭证
        db: 数据库会话

    Returns:
        str: tenant_id
    """
    tenant = await get_current_tenant_from_request(request, credentials, db)
    return tenant.id


def tenant_required():
    """
    装饰器：要求租户认证

    用于保护需要租户隔离的API端点
    """
    return Depends(get_current_tenant_from_request)


def tenant_id_required():
    """
    装饰器：要求tenant_id

    用于只需要tenant_id而不需要完整租户对象的端点
    """
    return Depends(get_tenant_from_token)


# 租户隔离装饰器
def with_tenant_isolation(func):
    """
    装饰器：为数据库查询添加租户隔离

    使用示例：
    @with_tenant_isolation
    async def get_user_data(user_id: str, db: Session):
        # 函数内部自动包含租户过滤
        query = db.query(User).filter(User.id == user_id)
        # 装饰器会自动添加 tenant_id 过滤条件
        return query.first()
    """
    async def wrapper(*args, **kwargs):
        # 检查是否有租户上下文
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant authentication required"
            )

        # 调用原始函数
        result = await func(*args, **kwargs)

        return result

    return wrapper


# 中间件工厂函数
def create_tenant_context_middleware():
    """
    创建线程安全的租户上下文中间件

    这个中间件会在每个请求开始时设置租户上下文，
    在请求结束时清除上下文，确保请求间隔离
    """
    import uuid

    async def middleware(request: Request, call_next):
        # 生成请求ID用于追踪
        request_id = str(uuid.uuid4())
        thread_id = threading.get_ident()

        logger.debug(
            "Request started",
            request_id=request_id,
            thread_id=thread_id,
            path=request.url.path,
            method=request.method
        )

        # 在请求开始时确保上下文是干净的
        try:
            tenant_context.clear()
            _request_id.set(request_id)

            # 处理请求
            response = await call_next(request)

            logger.debug(
                "Request completed",
                request_id=request_id,
                thread_id=thread_id,
                status_code=response.status_code
            )

        except Exception as e:
            logger.error(
                "Request error",
                request_id=request_id,
                thread_id=thread_id,
                error=str(e),
                path=request.url.path
            )
            raise
        finally:
            # 在请求结束时清除上下文（确保在finally中执行）
            try:
                tenant_context.clear()
            except Exception as cleanup_error:
                logger.warning(
                    "Error during context cleanup",
                    request_id=request_id,
                    error=str(cleanup_error)
                )

        return response

    return middleware


# 租户数据隔离辅助函数
def add_tenant_filter(query, tenant_id_field_name: str = "tenant_id"):
    """
    为SQLAlchemy查询添加租户过滤条件

    Args:
        query: SQLAlchemy查询对象
        tenant_id_field_name: 租户ID字段名

    Returns:
        添加了租户过滤的查询对象
    """
    tenant_id = get_current_tenant_id()
    if tenant_id:
        query = query.filter(getattr(query.column_descriptions[0]['type'], tenant_id_field_name) == tenant_id)

    return query


# 批量数据隔离函数
def filter_by_tenant(data_list: list, tenant_id_field: str = "tenant_id") -> list:
    """
    过滤数据列表，只返回属于当前租户的数据

    Args:
        data_list: 数据列表
        tenant_id_field: 租户ID字段名

    Returns:
        过滤后的数据列表
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return []

    return [
        item for item in data_list
        if getattr(item, tenant_id_field, None) == tenant_id
    ]