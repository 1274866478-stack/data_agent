"""
API认证中间件模块
提供API Key和JWT Token认证机制
支持Clerk托管认证服务集成
"""

from fastapi import Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.app.core.config import settings
from src.app.core.jwt_utils import JWTValidationError, validate_api_key_and_token

logger = logging.getLogger(__name__)


class APIKeyAuth(BaseHTTPMiddleware):
    """API Key认证中间件"""

    def __init__(self, app):
        super().__init__(app)
        # 如果设置了API密钥，则启用认证
        self.auth_required = bool(settings.api_key)
        self.security = HTTPBearer(auto_error=False)

    async def dispatch(self, request: Request, call_next):
        """
        处理请求认证
        """
        # 如果未设置API密钥，则跳过认证
        if not self.auth_required:
            return await call_next(request)

        # 豁免某些路径不需要认证
        if self._is_public_path(request.url.path):
            return await call_next(request)

        try:
            # 尝试从Authorization header中获取API密钥
            credentials: HTTPAuthorizationCredentials = await self.security(request)

            if credentials is None:
                # 尝试从查询参数中获取API密钥
                api_key = request.query_params.get("api_key")
                if not api_key:
                    return self._auth_error_response("Missing API key")
            else:
                api_key = credentials.credentials

            # 验证API密钥
            if not self._validate_api_key(api_key):
                logger.warning(f"Invalid API key attempt from {request.client.host}")
                return self._auth_error_response("Invalid API key")

            # 认证成功，记录请求
            logger.info(
                "Authenticated request from %s to %s",
                request.client.host,
                request.url.path,
            )

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._auth_error_response("Authentication failed")

        # 继续处理请求
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """
        检查路径是否为公共路径（不需要认证）
        """
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

        # 检查是否匹配公共路径
        for public_path in public_paths:
            if path == public_path or path.startswith(public_path):
                return True

        return False

    def _validate_api_key(self, api_key: str) -> bool:
        """
        验证API密钥
        """
        if not api_key or not settings.api_key:
            return False

        return api_key == settings.api_key

    def _auth_error_response(self, message: str) -> JSONResponse:
        """
        返回认证错误响应
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication Required",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
        )


class JWTAuth(HTTPBearer):
    """JWT认证依赖"""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Dict[str, Any]:
        """
        验证JWT Token并返回用户信息
        """
        # 检查路径是否为公共路径
        if self._is_public_path(request.url.path):
            return {"auth_type": "public", "user_info": None}

        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            # 开发环境：允许无认证访问
            if settings.environment == "development":
                logger.warning("开发环境：无认证凭证，使用默认用户")
                return {
                    "auth_type": "development",
                    "user_info": {
                        "user_id": "dev_user",
                        "tenant_id": "default_tenant",
                        "email": "dev@example.com"
                    }
                }
            raise self._auth_error_response("Missing authorization credentials")

        try:
            # 开发环境：接受特殊的开发token
            if settings.environment == "development" and credentials.credentials == "dev_token":
                logger.warning("开发环境：使用开发token")
                return {
                    "auth_type": "development",
                    "is_authenticated": True,
                    "user_info": {
                        "user_id": "dev_user",
                        "tenant_id": "default_tenant",
                        "email": "dev@example.com"
                    }
                }

            # 验证JWT Token
            auth_result = await validate_api_key_and_token(
                authorization=credentials.credentials
            )

            if not auth_result["is_authenticated"]:
                raise self._auth_error_response("Invalid authentication")

            logger.info(
                f"JWT authentication successful for user: {auth_result['user_info'].get('user_id')}"
            )

            return auth_result

        except JWTValidationError as e:
            logger.warning(f"JWT authentication failed: {e}")
            raise self._auth_error_response(str(e))
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise self._auth_error_response("Authentication failed")

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公共路径"""
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/api/v1/auth/",  # 认证端点本身
        ]

        for public_path in public_paths:
            if path == public_path or path.startswith(public_path):
                return True
        return False

    def _auth_error_response(self, message: str):
        """返回认证错误响应"""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Authentication Failed",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
        )


class HybridAuth:
    """混合认证（支持JWT和API Key）"""

    def __init__(self):
        self.jwt_auth = JWTAuth(auto_error=False)
        self.api_key_auth = HTTPBearer(auto_error=False)

    async def __call__(self, request: Request) -> Dict[str, Any]:
        """
        支持JWT Token和API Key的混合认证
        """
        # 检查路径是否为公共路径
        if self._is_public_path(request.url.path):
            return {"auth_type": "public", "user_info": None}

        # 尝试JWT认证
        try:
            # 从Authorization header获取token
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                auth_result = await validate_api_key_and_token(
                    authorization=authorization
                )
                if auth_result["is_authenticated"]:
                    return auth_result
        except Exception:
            pass  # JWT认证失败，继续尝试API Key

        # 尝试API Key认证
        try:
            api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
            if api_key:
                auth_result = await validate_api_key_and_token(api_key=api_key)
                if auth_result["is_authenticated"]:
                    return auth_result
        except Exception:
            pass  # API Key认证失败

        # 两种认证都失败
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Authentication Required",
                "message": "Valid JWT token or API key required",
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公共路径"""
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/api/v1/auth/",
        ]

        for public_path in public_paths:
            if path == public_path or path.startswith(public_path):
                return True
        return False


# 创建认证依赖实例
jwt_auth = JWTAuth()
hybrid_auth = HybridAuth()


async def get_current_user_with_tenant(
    auth_result: Dict[str, Any] = Depends(jwt_auth)
) -> Dict[str, Any]:
    """
    获取当前用户信息（包含租户ID）
    用于需要认证的API端点

    开发环境下允许无认证访问，使用默认租户
    """
    from fastapi import HTTPException

    # 开发环境：允许无认证访问
    if settings.environment == "development":
        if auth_result["auth_type"] == "public" or not auth_result.get("user_info"):
            logger.warning("开发环境：使用默认租户（无认证）")
            return {
                "user_id": "dev_user",
                "tenant_id": "default_tenant",
                "auth_type": "development",
                "email": "dev@example.com"
            }

    # 生产环境：严格认证
    if auth_result["auth_type"] == "public" or not auth_result.get("user_info"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    user_info = auth_result["user_info"]

    # 确保用户信息包含租户ID
    if not user_info.get("tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User missing tenant_id"
        )

    # 返回用户对象（兼容现有代码）
    user = type('User', (), {
        'id': user_info.get('user_id'),
        'tenant_id': user_info.get('tenant_id'),
        'email': user_info.get('email'),
        'first_name': user_info.get('first_name'),
        'last_name': user_info.get('last_name'),
        'is_verified': user_info.get('is_verified', False),
        'auth_type': auth_result.get('auth_type'),
        'raw_info': user_info
    })()

    return user


async def get_current_user_optional(
    auth_result: Dict[str, Any] = Depends(jwt_auth)
) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息（可选）
    用于可选认证的API端点
    """
    if auth_result["auth_type"] == "public" or not auth_result.get("user_info"):
        return None

    return auth_result["user_info"]


def create_api_key_auth():
    """
    创建API Key认证中间件实例
    """
    return APIKeyAuth
