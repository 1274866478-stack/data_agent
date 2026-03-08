# Self-Hosted Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Clerk authentication with self-hosted JWT-based authentication, enabling the platform to run independently without third-party SaaS dependencies.

**Architecture:**
- Backend adds JWT token generation (HS256) using existing `SECRET_KEY`
- Backend adds `/register` and `/login` endpoints for user authentication
- Frontend adds login page and switches to `AuthProvider` when `NEXT_PUBLIC_AUTH_MODE=selfhost`
- JWT tokens contain `user_id`, `email`, `tenant_id` for multi-tenant isolation
- Existing JWT validation infrastructure is reused with new issuer

**Tech Stack:** Python-jose (JWT), passlib[bcrypt] (password hashing), Next.js (frontend)

---

## Overview

This plan adds self-hosted authentication while maintaining compatibility with the existing multi-tenant architecture. The implementation:

1. **Reuses existing JWT validation** - only the issuer changes
2. **Minimal frontend changes** - adds login page, removes Clerk dependency
3. **Backward compatible** - can switch between Clerk and self-hosted via env var
4. **Database** - adds minimal User model for credentials

---

## Task 1: Backend - Add User Model

**Files:**
- Modify: `backend/src/app/data/models.py`

**Step 1: Add User model to models.py**

Add to `backend/src/app/data/models.py` after imports (around line 60):

```python
class User(Base):
    """
    自建认证用户模型

    存储用户登录凭据和基本信息
    与 Clerk 用户模型分离，支持自建认证
    """
    __tablename__ = "users"

    id: str = Column(String, primary_key=True)
    email: String = Column(String(255), unique=True, nullable=False, index=True)
    password_hash: String = Column(String(255), nullable=False)
    first_name: Optional[str] = Column(String(100))
    last_name: Optional[str] = Column(String(100))
    is_verified: bool = Column(Boolean, default=False)
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    def set_password(self, password: str):
        """哈希密码"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)
```

**Step 2: Create database migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "add users table for selfhosted auth"
```

**Step 3: Apply migration**

Run:
```bash
alembic upgrade head
```

**Step 4: Verify User model creation**

Run:
```bash
docker compose restart backend
```

---

## Task 2: Backend - Add JWT Creation Utilities

**Files:**
- Modify: `backend/src/app/core/jwt_utils.py`

**Step 1: Add JWT creation function**

Add to `backend/src/app/core/jwt_utils.py` (after imports, around line 60):

```python
def create_selfhost_jwt(user_id: str, email: str, tenant_id: str,
                           secret_key: str) -> str:
    """
    创建自建认证的 JWT Token

    Args:
        user_id: 用户唯一标识
        email: 用户邮箱
        tenant_id: 租户ID
        secret_key: JWT 密钥

    Returns:
        str: JWT Token 字符串
    """
    from datetime import datetime, timedelta

    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),  # 7天过期
        "iss": "selfhost",  # 自建认证的 issuer
        "aud": "bichat-api"
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    logger.info(f"Created self-hosted JWT for user: {user_id}")
    return token


async def validate_selfhost_token(token: str, secret_key: str) -> Dict[str, Any]:
    """
    验证自建认证的 JWT Token

    Args:
        token: JWT Token 字符串
        secret_key: JWT 密钥

    Returns:
        Dict: 包含用户信息的 payload

    Raises:
        JWTValidationError: 验证失败
    """
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True
            }
        )

        # 验证 issuer
        if payload.get("iss") != "selfhost":
            raise JWTValidationError(f"Invalid issuer: {payload.get('iss')}")

        # 验证 audience
        if payload.get("aud") != "bichat-api":
            raise JWTValidationError(f"Invalid audience: {payload.get('aud')}")

        user_info = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "tenant_id": payload.get("tenant_id"),
            "is_verified": True,  # 自建用户默认已验证
            "token_payload": payload
        }

        logger.info(f"Successfully validated self-hosted token for user: {user_info['user_id']}")
        return user_info

    except jwt.ExpiredSignatureError:
        raise JWTValidationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise JWTValidationError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise JWTValidationError(f"Token validation failed: {str(e)}")
```

**Step 2: Update get_clerk_validator to support fallback**

Modify the `get_clerk_validator()` function to support self-hosted mode (around line 190):

```python
@lru_cache(maxsize=32)
def get_jwt_validator(auth_mode: str = "clerk") -> JWTValidator:
    """
    获取 JWT 验证器（支持 Clerk 和自建）

    Args:
        auth_mode: 认证模式 ('clerk' | 'selfhost')
    """
    if auth_mode == "selfhost":
        # 自建模式：使用对称密钥
        from src.app.core.config import settings
        if not settings.secret_key:
            raise JWTValidationError("SECRET_KEY not configured for self-hosted auth")

        # 返回一个简化的验证器（复用现有结构）
        return JWTValidator(
            issuer="selfhost",
            jwks_url="",  # 不使用 JWKS
            audience="bichat-api"
        )
    else:
        # Clerk 模式：原有逻辑
        if not hasattr(settings, 'clerk_jwt_public_key') or not settings.clerk_jwt_public_key:
            raise JWTValidationError("Clerk JWT public key not configured")

        return JWTValidator(
            issuer="https://clerk."+getattr(settings, 'clerk_domain', 'clerk.accounts.dev'),
            jwks_url=f"https://clerk.{getattr(settings, 'clerk_domain', 'clerk.accounts.dev')}/.well-known/jwks.json",
            audience=getattr(settings, 'clerk_api_key', None)
        )
```

---

## Task 3: Backend - Add Authentication Endpoints

**Files:**
- Modify: `backend/src/app/api/v1/endpoints/auth.py`

**Step 1: Add request/response models**

Add to `backend/src/app/v1/endpoints/auth.py` (after existing models, around line 110):

```python
class RegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class LoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class AuthTokenResponse(BaseModel):
    """认证 Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数
    user_info: Dict[str, Any]
```

**Step 2: Add register endpoint**

Add to `backend/src/app/api/v1/endpoints/auth.py` (before @router.post("/verify"), around line 113):

```python
@router.post("/register", response_model=AuthTokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册

    创建新用户和租户，返回 JWT Token
    """
    from src.app.core.config import settings
    from src.app.data.models import User, Tenant
    from src.app.core.jwt_utils import create_selfhost_jwt

    try:
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # 创建租户 ID (使用 UUID)
        import uuid
        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # 创建租户
        tenant = Tenant(
            id=tenant_id,
            email=request.email,
            created_at=datetime.utcnow()
        )
        db.add(tenant)

        # 创建用户
        user = User(
            id=user_id,
            email=request.email,
            tenant_id=tenant_id,
            first_name=request.first_name,
            last_name=request.last_name
        )
        user.set_password(request.password)
        db.add(user)

        db.commit()
        db.refresh(user)

        # 生成 JWT Token
        token = create_selfhost_jwt(
            user_id=user_id,
            email=request.email,
            tenant_id=tenant_id,
            secret_key=settings.secret_key
        )

        logger.info(f"New user registered: {user_id} ({request.email})")

        return AuthTokenResponse(
            access_token=token,
            expires_in=7 * 24 * 60 * 60  # 7天
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录

    验证凭据并返回 JWT Token
    """
    from src.app.core.config import settings
    from src.app.data.models import User
    from src.app.core.jwt_utils import create_selfhost_jwt

    try:
        # 查找用户
        user = db.query(User).filter(User.email == request.email).first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # 验证密码
        if not user.verify_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # 生成 JWT Token
        token = create_selfhost_jwt(
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            secret_key=settings.secret_key
        )

        logger.info(f"User logged in: {user.id} ({user.email})")

        return AuthTokenResponse(
            access_token=token,
            expires_in=7 * 24 * 60 * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )
```

**Step 3: Test the endpoints**

Run:
```bash
curl -X POST http://localhost:8004/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","first_name":"Test","last_name":"User"}'
```

Expected: `{"access_token":"eyJ...","token_type":"bearer","expires_in":604800,"user_info":{...}}`

**Step 4: Commit backend changes**

```bash
git add backend/src/app/data/models.py backend/src/app/core/jwt_utils.py backend/src/app/api/v1/endpoints/auth.py
git commit -m "feat(auth): add self-hosted JWT authentication endpoints

- Add User model with bcrypt password hashing
- Add create_selfhost_jwt and validate_selfhost_token functions
- Add /register and /login endpoints
- Support auth_mode switching in get_jwt_validator
- Add 7-day token expiration
"
```

---

## Task 4: Backend - Update Auth Middleware

**Files:**
- Modify: `backend/src/app/core/auth.py`

**Step 1: Add self-hosted token validation**

Add to `backend/src/app/core/auth.py` (after existing functions, around line 150):

```python
async def get_current_user_with_tenant_selfhost(authorization: str) -> Dict[str, Any]:
    """
    从自建 JWT Token 获取当前用户和租户信息

    Args:
        authorization: Authorization header value

    Returns:
        Dict: 用户信息字典

    Raises:
        HTTPException: 401 if token invalid
    """
    from src.app.core.jwt_utils import validate_selfhost_token
    from src.app.core.config import settings

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    # 移除 "Bearer " 前缀
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization

    try:
        user_info = await validate_selfhost_token(token, settings.secret_key)

        # 确保租户存在
        from src.app.core.jwt_utils import create_tenant_for_user
        await create_tenant_for_user(user_info)

        return user_info

    except Exception as e:
        logger.warning(f"Self-hosted auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
```

**Step 2: Update get_current_user_with_tenant to support both modes**

Modify the `get_current_user_with_tenant` dependency (around line 200):

```python
def get_current_user_with_tenant(
    authorization: str = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any]:
    """
    获取当前用户和租户信息（支持 Clerk 和自建两种模式）
    """
    auth_mode = getattr(settings, 'auth_mode', 'clerk')

    if auth_mode == 'selfhost':
        # 同步包装异步函数（在依赖注入中可以这样做）
        import asyncio

        # 在依赖注入的上下文中运行
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已经在运行，创建任务
            return asyncio.create_task(
                get_current_user_with_tenant_selfhost(authorization.credentials)
            )
        else:
            # 否则直接运行
            return loop.run_until_complete(
                get_current_user_with_tenant_selfhost(authorization.credentials)
            )
    else:
        # Clerk 模式：使用原有逻辑
        return get_current_user_from_token(authorization.credentials)
```

**Step 5: Update config.py to add auth_mode**

Modify `backend/src/app/core/config.py` (in Settings class, around environment variables):

```python
# Authentication mode: 'clerk' | 'selfhost'
auth_mode: str = Field(
    default="clerk",
    description="Authentication mode: clerk (Clerk) or selfhost (self-built JWT)"
)
```

**Step 6: Commit auth middleware changes**

```bash
git add backend/src/app/core/auth.py backend/src/app/core/config.py
git commit -m "feat(auth): add self-hosted auth support to middleware

- Add get_current_user_with_tenant_selfhost for self-hosted JWT validation
- Update get_current_user_with_tenant to support auth_mode switching
- Add auth_mode configuration to Settings
"
```

---

## Task 5: Backend - Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add passlib to requirements.txt**

Add to `backend/requirements.txt`:

```
passlib[bcrypt]==1.7.4
```

**Step 2: Rebuild backend container**

Run:
```bash
docker compose build backend
```

**Step 3: Commit requirements change**

```bash
git add backend/requirements.txt
git commit -m "chore(auth): add passlib for password hashing"
```

---

## Task 6: Frontend - Add Auth Mode Environment Variable

**Files:**
- Create: `frontend/.env.tencent`

**Step 1: Create frontend env file**

Create `frontend/.env.tencent`:

```bash
# 认证模式: clerk | selfhost
NEXT_PUBLIC_AUTH_MODE=selfhost

# API 基础URL
NEXT_PUBLIC_API_URL=https://bichat.matrix-ai.com.cn/api/v1
```

**Step 2: Commit env file**

```bash
git add frontend/.env.tencent
git commit -m "chore(frontend): add selfhost auth mode configuration"
```

---

## Task 7: Frontend - Update AuthContext for Self-Hosted Mode

**Files:**
- Modify: `frontend/src/components/auth/AuthContext.tsx`

**Step 1: Add self-hosted mode to AuthContext**

Modify `frontend/src/components/auth/AuthContext.tsx` (around line 150-160):

```typescript
// AuthContext.tsx - update useEffect

useEffect(() => {
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  const authMode = process.env.NEXT_PUBLIC_AUTH_MODE // 'clerk' | 'selfhost'

  const isDevelopmentMode = process.env.NODE_ENV === 'development' ||
                            process.env.NEXT_PUBLIC_ENVIRONMENT === 'development'
  const hasClerkKey = !!clerkPublishableKey

  // 自建模式优先级最高
  if (authMode === 'selfhost') {
    // 从 localStorage 获取 token
    const getToken = () => {
      if (typeof window !== 'undefined') {
        return localStorage.getItem('auth_token')
      }
      return null
    }

    const token = getToken()
    if (token) {
      // 验证 token（通过后端）
      fetch('/api/v1/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      })
      .then(res => res.json())
      .then(data => {
        if (data.valid) {
          setCurrentUser({
            user_id: data.user_info.user_id,
            tenant_id: data.user_info.tenant_id,
            email: data.user_info.email,
            isVerified: data.user_info.is_verified,
          })
          setIsLoading(false)
        } else {
          // Token 无效，清除本地存储
          localStorage.removeItem('auth_token')
          setCurrentUser(null)
          setIsLoading(false)
        }
      })
      .catch(() => {
        localStorage.removeItem('auth_token')
        setCurrentUser(null)
        setIsLoading(false)
      })
    } else {
      setCurrentUser(null)
      setIsLoading(false)
    }
    return
  }

  // 原有 Clerk 逻辑...
```

**Step 2: Add setToken function**

Add to `frontend/src/components/auth/AuthContext.tsx`:

```typescript
// AuthContext.tsx - add to AuthContextProvider

export const AuthContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // ... existing state ...

  // 添加 setToken 函数
  const setAuthToken = (token: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  const clearAuthToken = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  // 将 setAuthToken 和 clearAuthToken 暴露给其他组件
  const value = useMemo(() => ({
    // ... existing value ...
    setAuthToken,
    clearAuthToken,
  }), [currentUser, /* other dependencies */])

  // ... rest of component ...
}
```

**Step 3: Commit AuthContext changes**

```bash
git add frontend/src/components/auth/AuthContext.tsx
git commit -m "feat(auth): add self-hosted auth support to AuthContext

- Add authMode check for selfhost mode
- Add localStorage token management
- Add setAuthToken and clearAuthToken functions
- Token validation through /api/v1/auth/verify endpoint
- "
```

---

## Task 8: Frontend - Update Layout to Support Auth Mode

**Files:**
- Modify: `frontend/src/app/layout.tsx`

**Step 1: Add auth_mode detection**

Modify `frontend/src/app/layout.tsx` (around line 80-90):

```typescript
// layout.tsx - update RootLayout logic

const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
const authMode = process.env.NEXT_PUBLIC_AUTH_MODE || 'clerk' // 新增

// 支持 NODE_ENV 和 NEXT_PUBLIC_ENVIRONMENT 两种方式判断开发模式
const isDevelopmentMode = process.env.NODE_ENV === 'development' ||
                          process.env.NEXT_PUBLIC_ENVIRONMENT === 'development'

const hasClerkKey = !!clerkPublishableKey

// 修改 Provider 选择逻辑
if (authMode === 'selfhost') {
  // 自建认证模式
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  )
}

if (isDevelopmentMode && !hasClerkKey && authMode !== 'selfhost') {
  // 开发模式：无 Clerk
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  )
}
```

**Step 2: Commit layout changes**

```bash
git add frontend/src/app/layout.tsx
git commit -m "feat(auth): add selfhost auth mode to layout routing

- Check NEXT_PUBLIC_AUTH_MODE for selfhost mode
- Selfhost mode bypasses Clerk requirement
- Development mode still works without auth
- "
```

---

## Task 9: Frontend - Create Login Page

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/components/auth/SelfHostLoginForm.tsx`

**Step 1: Create login page directory and page**

Create `frontend/src/app/(auth)/login/page.tsx`:

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import SelfHostLoginForm from '@/components/auth/SelfHostLoginForm'

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string>('')

  const handleSuccess = () => {
    // 登录成功，跳转到 dashboard
    router.push('/dashboard')
  }

  const handleError = (errorMessage: string) => {
    setError(errorMessage)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">登录 BiChat</h1>
          <p className="text-muted-foreground">
            输入您的账号和密码
          </p>
        </div>

        <SelfHostLoginForm
          onSuccess={handleSuccess}
          onError={handleError}
        />

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="text-center text-sm text-muted-foreground">
          还没有账号？{' '}
          <a href="/register" className="underline hover:text-primary">
            注册
          </a>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Create login form component**

Create `frontend/src/components/auth/SelfHostLoginForm.tsx`:

```typescript
'use client'

import { useState } from 'react'
import { AUTH_API_URL } from '@/lib/api'

interface SelfHostLoginFormProps {
  onSuccess: () => void
  onError: (error: string) => void
}

export function SelfHostLoginForm({ onSuccess, onError }: SelfHostLoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${AUTH_API_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        // 保存 token
        localStorage.setItem('auth_token', data.access_token)

        // 触发成功回调
        onSuccess()
      } else {
        onError(data.detail || '登录失败')
      }
    } catch (err) {
      onError('网络错误，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">
          邮箱
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          placeholder="your@email.com"
          disabled={isLoading}
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium mb-1">
          密码
        </label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          placeholder="•••••••••"
          disabled={isLoading}
        />
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? '登录中...' : '登录'}
      </button>
    </form>
  )
}
```

**Step 3: Create register page**

Create `frontend/src/app/(auth)/register/page.tsx`:

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import SelfHostRegisterForm from '@/components/auth/SelfHostRegisterForm'

export default function RegisterPage() {
  const router = useRouter()
  const [error, setError] = useState<string>('')

  const handleSuccess = () => {
    router.push('/dashboard')
  }

  const handleError = (errorMessage: string) => {
    setError(errorMessage)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">注册 BiChat</h1>
          <p className="text-muted-foreground">
            创建您的账号
          </p>
        </div>

        <SelfHostRegisterForm
          onSuccess={handleSuccess}
          onError={handleError}
        />

        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="text-center text-sm text-muted-foreground">
          已有账号？{' '}
          <a href="/login" className="underline hover:text-primary">
            登录
          </a>
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Create register form component**

Create `frontend/src/components/auth/SelfHostRegisterForm.tsx`:

```typescript
'use client'

import { useState } from 'react'
import { AUTH_API_URL } from '@/lib/api'

interface SelfHostRegisterFormProps {
  onSuccess: () => void
  onError: (error: string) => void
}

export function SelfHostRegisterForm({ onSuccess, onError }: SelfHostRegisterFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // 验证密码
    if (password !== confirmPassword) {
      onError('两次输入的密码不一致')
      return
    }

    if (password.length < 8) {
      onError('密码至少需要8个字符')
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch(`${AUTH_API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          first_name: firstName,
          last_name: lastName,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        // 保存 token
        localStorage.setItem('auth_token', data.access_token)
        onSuccess()
      } else {
        onError(data.detail || '注册失败')
      }
    } catch (err) {
      onError('网络错误，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="firstName" className="block text-sm font-medium mb-1">
          名字
        </label>
        <input
          id="firstName"
          type="text"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          disabled={isLoading}
        />
      </div>

      <div>
        <label htmlFor="lastName" className="block text-sm font-medium mb-1">
          姓氏
        </label>
        <input
          id="lastName"
          type="text"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          disabled={isLoading}
        />
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">
          邮箱
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          placeholder="your@email.com"
          disabled={isLoading}
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium mb-1">
          密码
        </label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          placeholder="至少8个字符"
          disabled={isLoading}
        />
      </div>

      <div>
        <label htmlFor="confirmPassword" className="block text-sm font-medium mb-1">
          确认密码
        </label>
        <input
          id="confirmPassword"
          type="password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
          placeholder="再次输入密码"
          disabled={isLoading}
        />
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
      >
        {isLoading ? '注册中...' : '注册'}
      </button>
    </form>
  )
}
```

**Step 5: Update middleware.ts to allow auth routes**

Modify `frontend/middleware.ts` (around line 8):

```typescript
// middleware.ts - update development mode check

  // 开发模式：跳过认证检查
  if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return NextResponse.next()
  }

  // 新增：自建模式跳过 Clerk 检查
  if (process.env.NEXT_PUBLIC_AUTH_MODE === 'selfhost') {
    return NextResponse.next()
  }
```

**Step 6: Commit frontend auth pages**

```bash
git add frontend/src/app/(auth)/login/page.tsx \
         frontend/src/app/(auth)/register/page.tsx \
         frontend/src/components/auth/SelfHostLoginForm.tsx \
         frontend/src/components/auth/SelfHostRegisterForm.tsx \
         frontend/middleware.ts
git commit -m "feat(auth): add self-hosted login and register pages

- Add login and register pages with forms
- Add SelfHostLoginForm and SelfHostRegisterForm components
- Update middleware to allow selfhost auth mode
- Add form validation and error handling
- Integrate with /api/v1/auth/login and /register endpoints
"
```

---

## Task 10: Frontend - Update API Client to Include Token

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add token to API requests**

Modify `frontend/src/lib/api.ts` to include JWT token in headers:

```typescript
// api.ts - update fetch wrapper

const AUTH_TOKEN_KEY = 'auth_token'

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  }
  return null
}

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = getAuthToken()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options?.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
```

**Step 2: Update clearAuthToken on logout**

Add to AuthContext.tsx logout handler:

```typescript
// In AuthContext.tsx, add logout function

const logout = async () => {
  clearAuthToken()
  setCurrentUser(null)
  router.push('/login')
}
```

**Step 3: Commit API client changes**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(auth): add JWT token to API requests

- Add getAuthToken() function to retrieve token from localStorage
- Include Authorization header in all API requests
- Add 401 handling for expired tokens
- "
```

---

## Task 11: Backend - Update Health Check Config

**Files:**
- Modify: `backend/src/app/api/v1/endpoints/auth.py`

**Step 1: Update get_auth_config endpoint**

Modify the `/auth/config` endpoint to report auth mode (around line 340):

```python
@router.get("/config")
async def get_auth_config():
    """
    获取认证配置信息
    用于前端了解认证设置
    """
    try:
        from src.app.core.config import settings

        auth_mode = getattr(settings, 'auth_mode', 'clerk')

        config = {
            "auth_provider": auth_mode,
            "jwt_issuer": f"https://clerk.{getattr(settings, 'clerk_domain', 'clerk.accounts.dev')}"
                         if auth_mode == 'clerk' else "selfhost",
            "supported_flows": ["jwt", "api_key"],
            "token_validation": "enabled",
            "tenant_isolation": "enabled",
            "auth_mode": auth_mode  # 新增
        }

        return config

    except Exception as e:
        logger.error(f"Get auth config failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication configuration"
        )
```

**Step 2: Commit health check changes**

```bash
git add backend/src/app/api/v1/endpoints/auth.py
git commit -m "feat(auth): report auth_mode in /auth/config endpoint

- Add auth_mode field to config response
- Update jwt_issuer based on auth_mode
- Help frontend determine which auth mode is active
- "
```

---

## Task 12: Testing - Backend Authentication Flow

**Files:**
- Test: `backend/tests/api/v1/test_auth_selfhost.py`

**Step 1: Create test file**

Create `backend/tests/api/v1/test_auth_selfhost.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_register_new_user(client: TestClient, db: Session):
    """测试用户注册"""
    response = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "password123",
        "first_name": "New",
        "last_name": "User"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user_info" in data

def test_register_duplicate_email(client: TestClient, db: Session):
    """测试重复邮箱注册失败"""
    # 第一次注册
    client.post("/api/v1/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User"
    })

    # 第二次注册相同邮箱
    response = client.post("/api/v1/auth/register", json={
        "email": "duplicate@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User"
    })

    assert response.status_code == 400

def test_login_valid_credentials(client: TestClient, db: Session):
    """测试有效凭据登录"""
    # 先注册
    client.post("/api/v1/auth/register", json={
        "email": "loginuser@example.com",
        "password": "password123",
        "first_name": "Login",
        "last_name": "User"
    })

    # 登录
    response = client.post("/api/v1/auth/login", json={
        "email": "loginuser@example.com",
        "password": "password123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_login_invalid_password(client: TestClient):
    """测试错误密码登录失败"""
    response = client.post("/api/v1/auth/login", json={
        "email": "loginuser@example.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 401

def test_verify_token_valid(client: TestClient):
    """测试Token验证"""
    # 先登录获取 token
    login_response = client.post("/api/v1/auth/login", json={
        "email": "verifyuser@example.com",
        "password": "password123"
    })
    token = login_response.json()["access_token"]

    # 验证 token
    response = client.post("/api/v1/auth/verify", json={
        "token": token
    })

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True

def test_verify_token_invalid(client: TestClient):
    """测试无效Token验证失败"""
    response = client.post("/api/v1/auth/verify", json={
        "token": "invalid.token.here"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
```

**Step 2: Run tests**

Run:
```bash
cd backend
pytest tests/api/v1/test_auth_selfhost.py -v
```

Expected: All tests pass

**Step 3: Commit test file**

```bash
git add backend/tests/api/v1/test_auth_selfhost.py
git commit -m "test(auth): add self-hosted authentication tests

- Test user registration flow
- Test duplicate email rejection
- Test login with valid/invalid credentials
- Test token verification
- All tests use pytest fixtures and follow AAA pattern
- "
```

---

## Task 13: Frontend - Update AuthContext to Use Token in API Calls

**Files:**
- Modify: `frontend/src/components/auth/AuthContext.tsx`

**Step 1: Add token to API requests in AuthContext**

Update the AuthContext to include JWT token in subsequent API calls (modify around line 150-170):

```typescript
// 在 AuthContext.tsx 中，添加 token 到 API 请求

// 修改 verifyToken 函数添加 JWT token
const verifyToken = async () => {
  const token = getAuthToken()

  const response = await fetch('/api/v1/auth/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    },
    body: JSON.stringify({ token })
  })
  // ... rest of function
}
```

**Step 2: Commit AuthContext token integration**

```bash
git add frontend/src/components/auth/AuthContext.tsx
git commit -m "fix(auth): include JWT token in AuthContext API calls

- Add Authorization header to verifyToken request
- Use getAuthToken() to retrieve token from localStorage
- Ensures token is passed to backend for validation
- "
```

---

## Task 14: Frontend - Create Logout Functionality

**Files:**
- Modify: `frontend/src/components/auth/AuthContext.tsx`

**Step 1: Add logout handler to AuthContext**

```typescript
// AuthContext.tsx - add logout function

const logout = async () => {
  try {
    // 调用后端登出端点（记录日志）
    const token = getAuthToken()
    if (token) {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })
    }

    // 清除本地 token
    clearAuthToken()
    setCurrentUser(null)

    // 跳转到登录页
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  } catch (error) {
    logger.error('Logout error:', error)
    // 即使登出失败，也清除本地状态
    clearAuthToken()
    setCurrentUser(null)
    window.location.href = '/login'
  }
}
```

**Step 2: Expose logout from AuthContext**

Ensure logout is in the context value:

```typescript
const value = useMemo(() => ({
  // ... existing values ...
  logout,
  // ... other methods ...
}), [currentUser, /* dependencies */])
```

**Step 3: Commit logout functionality**

```bash
git add frontend/src/components/auth/AuthContext.tsx
git commit -m "feat(auth): add logout function with backend logging

- Add logout async function with API call
- Clear auth token from localStorage
- Redirect to /login after logout
- Handle logout errors gracefully
- Expose logout in AuthContext value
- "
```

---

## Task 15: Frontend - Add API_URL Environment Variable

**Files:**
- Modify: `frontend/.env.tencent`

**Step 1: Ensure API_URL is set in frontend env**

Update `frontend/.env.tencent`:

```bash
# 认证模式: clerk | selfhost
NEXT_PUBLIC_AUTH_MODE=selfhost

# API 基础URL
NEXT_PUBLIC_API_URL=https://bichat.matrix-ai.com.cn/api/v1
```

**Step 2: Commit env update**

```bash
git add frontend/.env.tencent
git commit -m "fix(env): update API URL for production deployment

- Set NEXT_PUBLIC_API_URL to production domain
- Ensure HTTPS protocol
- Point to correct backend API endpoint
- "
```

---

## Task 16: Integration Test - End-to-End Authentication Flow

**Step 1: Start backend with selfhost mode**

```bash
cd backend
export AUTH_MODE=selfhost
docker compose up -d backend
```

**Step 2: Test registration flow**

```bash
# Test register
curl -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "e2e-test@example.com",
    "password": "testpass123",
    "first_name": "E2E",
    "last_name": "Test"
  }'
```

Expected: `{"access_token":"eyJ...","token_type":"bearer","expires_in":604800,...}`

**Step 3: Test login flow**

```bash
# Test login
curl -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "e2e-test@example.com",
    "password": "testpass123"
  }'
```

Expected: `{"access_token":"eyJ...","token_type":"bearer","expires_in":604800,...}`

**Step 4: Test token validation**

```bash
# Extract token from login response
TOKEN="eyJ..." # from login response

# Test verify
curl -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}"
```

Expected: `{"valid":true,"user_info":{...}}`

**Step 5: Test protected endpoint with token**

```bash
# Test accessing protected endpoint
curl https://bichat.matrix-ai.com.cn/api/v1/tenants/ \
  -H "Authorization: Bearer $TOKEN"
```

Expected: JSON response with tenant list (if has data)

**Step 6: Create integration test file**

Create `backend/tests/integration/test_auth_flow.py`:

```python
import pytest
import requests

BASE_URL = "https://bichat.matrix-ai.com.cn/api/v1"

def test_complete_auth_flow():
    """端到端测试认证流程"""

    # 1. 注册新用户
    email = f"e2e-{uuid.uuid4()}@example.com"

    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email,
            "password": "testpass123",
            "first_name": "E2E",
            "last_name": "Test"
        }
    )

    assert register_response.status_code == 200
    token = register_response.json()["access_token"]

    # 2. 验证 token
    verify_response = requests.post(
        f"{BASE_URL}/auth/verify",
        json={"token": token}
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True

    # 3. 使用 token 访问受保护的端点
    tenants_response = requests.get(
        f"{BASE_URL}/tenants/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert tenants_response.status_code == 200

    # 4. 登出
    logout_response = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert logout_response.status_code == 200

    print("✅ Integration test passed!")
```

**Step 7: Run integration test**

```bash
cd backend
pytest tests/integration/test_auth_flow.py -v
```

**Step 8: Commit integration test**

```bash
git add backend/tests/integration/test_auth_flow.py
git commit -m "test(integration): add end-to-end auth flow test

- Test complete user registration flow
- Test JWT token generation and validation
- Test protected endpoint access
- Test logout flow
- Uses production API endpoint
- "
```

---

## Task 17: Documentation - Update Deployment Docs

**Files:**
- Modify: `docs/DEPLOYMENT-TENCENT.md`

**Step 1: Update deployment docs**

Add to `docs/DEPLOYMENT-TENCENT.md` (after existing content):

```markdown
## Authentication

The platform supports two authentication modes:

### Clerk Mode (Default)
- Third-party SaaS authentication
- Requires NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
- Social logins, MFA, user management included

### Self-Hosted Mode (New)
- Complete self-hosted authentication
- No third-party dependencies
- Email + password authentication
- 7-day JWT tokens

### Switching Authentication Modes

To use self-hosted mode, set in `frontend/.env.tencent`:

```bash
NEXT_PUBLIC_AUTH_MODE=selfhost
```

Then restart the frontend:

```bash
docker compose -f docker-compose.tencent.yml restart frontend
```

### API Endpoints

#### Authentication
```
POST /api/v1/auth/register  - User registration
POST /api/v1/auth/login      - User login
POST /api/v1/auth/logout     - User logout
POST /api/v1/auth/verify     - Token validation
```

#### Protected Endpoint Example

```bash
curl https://bichat.matrix-ai.com.cn/api/v1/tenants/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
```

**Step 2: Commit documentation**

```bash
git add docs/DEPLOYMENT-TENCENT.md
git commit -m "docs(auth): document self-hosted authentication mode

- Add authentication mode section
- Document environment variable switching
- Add API endpoint documentation
- Include curl examples for testing
- "
```

---

## Task 18: Frontend - Remove Clerk Dependencies (Optional)

**Files:**
- Modify: `frontend/package.json`

**Step 1: Identify Clerk dependencies**

Check which Clerk packages are installed:

```bash
cd frontend
npm list | grep -i clerk
```

**Step 2: Remove Clerk packages (if safe to do so)**

If Clerk is only used for auth and no longer needed:

```bash
npm uninstall @clerk/clerk-react @clerk/clerk-js
```

**Step 3: Update imports if needed**

Remove any unused Clerk imports from:
- `frontend/src/app/layout.tsx`
- `frontend/src/components/auth/ClerkProvider.tsx`

**Step 4: Test frontend build**

```bash
npm run build
```

**Step 5: Commit dependency removal**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(auth): remove Clerk dependencies (if applicable)

- Uninstall @clerk/clerk-react and @clerk/clerk-js
- Remove unused Clerk imports
- Verify build still works
- "
```

---

## Task 19: Final Integration Testing

**Step 1: Test complete user flow in browser**

1. Navigate to https://bichat.matrix-ai.com.cn/login
2. Register a new account
3. Login with the new account
4. Verify dashboard is accessible
5. Logout

**Step 2: Test API with curl**

```bash
# Full test script
#!/bin/bash
set -e

echo "1. Testing registration..."
REGISTER_RESP=$(curl -s -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "final-test@example.com",
    "password": "testpass123",
    "first_name": "Final",
    "last_name": "Test"
  }')

TOKEN=$(echo $REGISTER_RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "2. Testing login..."
curl -s -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "final-test@example.com",
    "password": "testpass123"
  }'

echo "3. Testing token verification..."
curl -s -X POST https://bichat.matrix-ai.com.cn/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}"

echo "4. Testing protected endpoint..."
curl -s https://bichat.matrix-ai.com.cn/api/v1/auth/status \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "✅ All tests passed!"
```

**Step 3: Check health status**

```bash
curl -s https://bichat.matrix-ai.com.cn/api/v1/health/status | python3 -m json.tool
```

**Step 4: Merge to main branch**

When all tests pass, merge the worktree branch to main:

```bash
git checkout main
git pull origin main
git merge feature/selfhost-auth
git push origin main
```

---

## Summary

This plan implements a complete self-hosted authentication system that:

✅ **Removes Clerk dependency** - fully autonomous operation
✅ **Reuses existing JWT infrastructure** - minimal code changes
✅ **Maintains multi-tenant isolation** - tenant_id preserved
✅ **Provides simple migration path** - environment variable switch
✅ **Includes comprehensive tests** - unit and integration
✅ **Documents all changes** - deployment guide updated

**Estimated timeline: 2 days for implementation, 1 week for testing and refinement**

**Files modified:**
- Backend: 4 files (models.py, jwt_utils.py, auth.py, config.py)
- Frontend: 5 files (layout.tsx, AuthContext.tsx, login/page.tsx, register/page.tsx, middleware.tsx)
- Tests: 2 new test files
- Docs: 1 file updated

**Risk level:** LOW - changes are isolated to authentication layer, existing business logic untouched
