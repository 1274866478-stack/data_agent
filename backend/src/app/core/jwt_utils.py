"""
JWT验证工具模块
提供Clerk/Auth0 JWT Token验证功能
支持多租户和用户信息提取
"""

import jwt
import httpx
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urljoin
import json
from functools import lru_cache

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    """JWT验证错误"""
    pass


class JWKSManager:
    """JWKS (JSON Web Key Set) 管理器"""

    def __init__(self):
        self.jwks_cache = {}
        self.cache_ttl = 3600  # 1小时缓存

    async def get_jwks(self, jwks_url: str) -> Dict[str, Any]:
        """获取JWKS，带缓存"""
        now = datetime.now()

        # 检查缓存
        if jwks_url in self.jwks_cache:
            cached_data, cached_time = self.jwks_cache[jwks_url]
            if (now - cached_time).seconds < self.cache_ttl:
                return cached_data

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()

                jwks_data = response.json()
                self.jwks_cache[jwks_url] = (jwks_data, now)
                logger.info(f"JWKS cached from {jwks_url}")
                return jwks_data

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")

            # 如果有缓存数据，即使过期也返回
            if jwks_url in self.jwks_cache:
                logger.warning(f"Using expired JWKS cache for {jwks_url}")
                return self.jwks_cache[jwks_url][0]

            raise JWTValidationError(f"Unable to fetch JWKS: {e}")


# 全局JWKS管理器
jwks_manager = JWKSManager()


class JWTValidator:
    """JWT验证器"""

    def __init__(self,
                 issuer: str,
                 jwks_url: str,
                 audience: Optional[str] = None):
        self.issuer = issuer
        self.jwks_url = jwks_url
        self.audience = audience

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        验证JWT Token并返回payload

        Args:
            token: JWT Token字符串

        Returns:
            Dict: 解码后的payload

        Raises:
            JWTValidationError: 验证失败
        """
        try:
            # 获取JWKS
            jwks = await jwks_manager.get_jwks(self.jwks_url)

            # 解码header获取kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')

            if not kid:
                raise JWTValidationError("Token missing 'kid' header")

            # 找到对应的公钥
            key = self._find_key_by_kid(jwks, kid)
            if not key:
                raise JWTValidationError(f"Key with kid '{kid}' not found in JWKS")

            # 验证token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": bool(self.audience)
                }
            )

            # 验证token是否包含必要信息
            self._validate_payload(payload)

            return payload

        except jwt.ExpiredSignatureError:
            raise JWTValidationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTValidationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise JWTValidationError(f"Token validation failed: {str(e)}")

    def _find_key_by_kid(self, jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
        """根据kid查找对应的公钥"""
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                return key
        return None

    def _validate_payload(self, payload: Dict[str, Any]):
        """验证payload包含必要信息"""
        required_fields = ['sub', 'iat', 'exp']
        for field in required_fields:
            if field not in payload:
                raise JWTValidationError(f"Token missing required field: {field}")


@lru_cache(maxsize=32)
def get_clerk_validator() -> JWTValidator:
    """获取Clerk JWT验证器"""
    if not hasattr(settings, 'clerk_jwt_public_key') or not settings.clerk_jwt_public_key:
        raise JWTValidationError("Clerk JWT public key not configured")

    return JWTValidator(
        issuer="https://clerk."+getattr(settings, 'clerk_domain', 'clerk.accounts.dev'),
        jwks_url=f"https://clerk.{getattr(settings, 'clerk_domain', 'clerk.accounts.dev')}/.well-known/jwks.json",
        audience=getattr(settings, 'clerk_api_key', None)
    )


async def validate_clerk_token(token: str) -> Dict[str, Any]:
    """
    验证Clerk JWT Token

    Args:
        token: Clerk JWT Token

    Returns:
        Dict: 包含用户信息的payload
    """
    try:
        validator = get_clerk_validator()
        payload = await validator.validate_token(token)

        # 提取用户信息
        user_info = {
            "user_id": payload.get('sub'),
            "email": payload.get('email'),
            "tenant_id": payload.get('tenant_id', extract_tenant_id_from_sub(payload.get('sub', ''))),
            "first_name": payload.get('given_name'),
            "last_name": payload.get('family_name'),
            "phone": payload.get('phone_number'),
            "is_verified": payload.get('email_verified', False),
            "token_payload": payload
        }

        logger.info(f"Successfully validated Clerk token for user: {user_info['user_id']}")
        return user_info

    except Exception as e:
        logger.error(f"Clerk token validation failed: {e}")
        raise


def extract_tenant_id_from_sub(sub: str) -> str:
    """
    从用户subject提取tenant_id
    如果没有特定格式，使用user_id作为tenant_id
    """
    # Clerk的sub格式通常是 user_id
    # 可以根据业务需求调整提取逻辑
    return sub


async def create_tenant_for_user(user_info: Dict[str, Any]) -> str:
    """
    为新用户创建租户记录

    Args:
        user_info: 用户信息字典

    Returns:
        str: tenant_id
    """
    from src.app.data.database import get_db
    from src.app.data.models import Tenant

    tenant_id = user_info['tenant_id']

    try:
        async with get_db() as session:
            # 检查租户是否已存在
            existing_tenant = await session.get(Tenant, tenant_id)

            if not existing_tenant:
                # 创建新租户
                new_tenant = Tenant(
                    id=tenant_id,
                    email=user_info.get('email'),
                    created_at=datetime.utcnow()
                )
                session.add(new_tenant)
                await session.commit()
                await session.refresh(new_tenant)

                logger.info(f"Created new tenant: {tenant_id}")

            return tenant_id

    except Exception as e:
        logger.error(f"Failed to create/update tenant: {e}")
        # 数据库操作失败，但仍返回tenant_id
        return tenant_id


async def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """
    从JWT Token获取当前用户信息

    Args:
        token: Authorization header中的Bearer token

    Returns:
        Dict: 用户信息
    """
    if not token:
        raise JWTValidationError("No token provided")

    # 移除Bearer前缀
    if token.startswith('Bearer '):
        token = token[7:]

    # 验证token
    user_info = await validate_clerk_token(token)

    # 确保租户存在
    await create_tenant_for_user(user_info)

    return user_info


def decode_token_without_validation(token: str) -> Dict[str, Any]:
    """
    不验证签名的情况下解码token（用于调试）

    Args:
        token: JWT Token

    Returns:
        Dict: 解码后的payload
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        logger.error(f"Failed to decode token without validation: {e}")
        raise JWTValidationError(f"Token decode failed: {str(e)}")


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    获取token过期时间

    Args:
        token: JWT Token

    Returns:
        Optional[datetime]: 过期时间，解析失败返回None
    """
    try:
        payload = decode_token_without_validation(token)
        exp_timestamp = payload.get('exp')

        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)

        return None
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    检查token是否过期

    Args:
        token: JWT Token

    Returns:
        bool: 是否过期
    """
    expiration = get_token_expiration(token)

    if expiration is None:
        return True  # 无法解析过期时间，认为已过期

    return datetime.utcnow() > expiration


def refresh_token_check(token: str, refresh_threshold_minutes: int = 15) -> bool:
    """
    检查token是否需要刷新

    Args:
        token: JWT Token
        refresh_threshold_minutes: 刷新阈值（分钟）

    Returns:
        bool: 是否需要刷新
    """
    expiration = get_token_expiration(token)

    if expiration is None:
        return True

    threshold_time = datetime.utcnow() + timedelta(minutes=refresh_threshold_minutes)
    return expiration <= threshold_time


async def validate_api_key_and_token(
    api_key: Optional[str] = None,
    authorization: Optional[str] = None
) -> Dict[str, Any]:
    """
    验证API密钥或JWT Token

    Args:
        api_key: API密钥
        authorization: Authorization header值

    Returns:
        Dict: 验证结果和用户信息

    Raises:
        JWTValidationError: 验证失败
    """
    # 开发模式：接受dev-mock-token
    if authorization:
        # authorization参数可能包含"Bearer "前缀，也可能不包含
        token = authorization.replace('Bearer ', '').strip()
        logger.info(f"🔍 DEBUG: token='{token}', environment='{settings.environment}'")
        if token == 'dev-mock-token' and settings.environment == 'development':
            logger.info("🔧 开发模式：接受mock token")
            return {
                "auth_type": "dev_mock",
                "user_info": {
                    "user_id": "anonymous",
                    "email": "admin@dataagent.local",
                    "tenant_id": "default_tenant",
                    "first_name": "Development",
                    "last_name": "User",
                    "is_verified": True
                },
                "is_authenticated": True
            }
        else:
            logger.warning(f"🔍 DEBUG: dev-mock-token check failed. token==dev-mock-token: {token == 'dev-mock-token'}, environment==development: {settings.environment == 'development'}")

    # 优先使用JWT Token
    if authorization:
        user_info = await get_current_user_from_token(authorization)
        return {
            "auth_type": "jwt",
            "user_info": user_info,
            "is_authenticated": True
        }

    # 回退到API Key验证
    elif api_key and settings.api_key and api_key == settings.api_key:
        return {
            "auth_type": "api_key",
            "user_info": {"user_id": "api_user", "tenant_id": "system"},
            "is_authenticated": True
        }

    else:
        raise JWTValidationError("No valid authentication provided")


# 导出的便捷函数
async def extract_user_from_request(authorization: str) -> Dict[str, Any]:
    """
    从请求头中提取用户信息的便捷函数

    Args:
        authorization: Authorization header值

    Returns:
        Dict: 用户信息
    """
    return await get_current_user_from_token(authorization)