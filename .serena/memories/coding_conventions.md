# Data Agent V4 编码规范和约定

## 后端 Python 规范

### 代码风格
- **代码格式化**: Black (默认配置)
- **导入排序**: isort (配置文件: `pyproject.toml`)
- **代码检查**: flake8 (配置文件: `.flake8`)
- **类型检查**: mypy strict模式

### 命名约定
```python
# 变量和函数: snake_case
user_name = "john"
def get_user_data():
    pass

# 类名: PascalCase
class UserService:
    pass

# 常量: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有变量: 前缀下划线
class MyClass:
    def __init__(self):
        self._private_var = "private"
        self.__very_private = "very private"
```

### 类型注解
```python
from typing import Optional, List, Dict, Any
from datetime import datetime

# 函数必须有完整的类型注解
async def create_user(
    name: str,
    email: str,
    age: Optional[int] = None
) -> User:
    return User(name=name, email=email, age=age)

# 使用类型别名
UserID = str
DatabaseConnection = Dict[str, Any]

def get_user(user_id: UserID) -> DatabaseConnection:
    pass
```

### 文档字符串 (Google Style)
```python
def calculate_price(
    base_price: float,
    discount_rate: float = 0.0,
    tax_rate: float = 0.1
) -> float:
    """计算商品最终价格。
    
    Args:
        base_price: 商品基础价格
        discount_rate: 折扣率，默认为0.0
        tax_rate: 税率，默认为0.1
        
    Returns:
        商品的最终价格
        
    Raises:
        ValueError: 当价格为负数时
        
    Example:
        >>> calculate_price(100.0, 0.1, 0.08)
        97.2
    """
    if base_price < 0:
        raise ValueError("Base price cannot be negative")
    
    discounted_price = base_price * (1 - discount_rate)
    final_price = discounted_price * (1 + tax_rate)
    return final_price
```

### 异步编程规范
```python
# 所有数据库操作必须是异步的
async def get_user_by_id(user_id: str) -> Optional[User]:
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

# 使用asyncio.gather处理并发操作
async def process_multiple_users(user_ids: List[str]) -> List[User]:
    tasks = [get_user_by_id(user_id) for user_id in user_ids]
    users = await asyncio.gather(*tasks)
    return [user for user in users if user is not None]
```

### 错误处理
```python
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

# 使用结构化日志记录错误
async def create_data_source(data: CreateDataSourceRequest) -> DataSource:
    try:
        # 业务逻辑
        result = await data_source_service.create(data)
        logger.info(
            "Data source created successfully",
            extra={
                "data_source_id": result.id,
                "tenant_id": data.tenant_id,
                "connection_type": data.connection_type
            }
        )
        return result
    except DatabaseError as e:
        logger.error(
            "Database error while creating data source",
            extra={
                "tenant_id": data.tenant_id,
                "error_code": e.error_code,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Internal database error"
        )
    except Exception as e:
        logger.error(
            "Unexpected error creating data source",
            extra={
                "tenant_id": data.tenant_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

### 数据库操作规范
```python
# 使用SQLAlchemy 2.0异步模式
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

# 租户隔离 - 所有查询必须包含tenant_id过滤
async def get_tenant_documents(
    session: AsyncSession,
    tenant_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Document]:
    query = (
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .where(Document.is_active == True)
        .offset(skip)
        .limit(limit)
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(query)
    return result.scalars().all()

# 批量操作
async def bulk_create_documents(
    session: AsyncSession,
    documents: List[Document]
) -> List[Document]:
    session.add_all(documents)
    await session.commit()
    return documents
```

### API端点规范
```python
from fastapi import APIRouter, Depends, HTTPException, status
from src.app.core.auth import get_current_user, tenant_required

router = APIRouter()

# 统一的响应格式
@router.get(
    "/data-sources",
    response_model=List[DataSourceResponse],
    dependencies=[Depends(tenant_required)]
)
async def list_data_sources(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> List[DataSourceResponse]:
    """获取当前租户的数据源列表"""
    try:
        data_sources = await data_source_service.get_by_tenant(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
            db=db
        )
        return [DataSourceResponse.from_orm(ds) for ds in data_sources]
    except Exception as e:
        logger.error(f"Error listing data sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list data sources"
        )
```

## 前端 TypeScript 规范

### 命名约定
```typescript
// 组件: PascalCase
export const DataSourceList: React.FC<DataSourceListProps> = () => {
  return <div>...</div>
}

// 变量和函数: camelCase
const userName = "john"
const getUserData = () => {}

// 常量: UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3

// 类型和接口: PascalCase
interface User {
  id: string
  name: string
  email: string
}

type APIResponse<T> = {
  data: T
  status: number
}
```

### 组件结构
```typescript
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/authStore'

interface UserListProps {
  onUserSelect?: (userId: string) => void
  className?: string
}

export const UserList: React.FC<UserListProps> = ({
  onUserSelect,
  className = ""
}) => {
  // 1. 状态定义
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // 2. 工具函数
  const { user } = useAuthStore()
  
  // 3. 副作用
  useEffect(() => {
    loadUsers()
  }, [])
  
  // 4. 事件处理函数
  const loadUsers = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await userService.getUsers()
      setUsers(response.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleUserClick = (userId: string) => {
    onUserSelect?.(userId)
  }
  
  // 5. 渲染
  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>
  
  return (
    <div className={`user-list ${className}`}>
      {users.map(user => (
        <div 
          key={user.id}
          onClick={() => handleUserClick(user.id)}
          className="user-item"
        >
          {user.name}
        </div>
      ))}
    </div>
  )
}
```

### 状态管理 (Zustand)
```typescript
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface User {
  id: string
  name: string
  email: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  updateUser: (userData: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      
      login: async (credentials) => {
        set({ isLoading: true })
        try {
          const response = await authService.login(credentials)
          set({
            user: response.user,
            token: response.token,
            isAuthenticated: true,
            isLoading: false
          })
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false
        })
      },
      
      refreshToken: async () => {
        const { token } = get()
        if (!token) throw new Error('No token available')
        
        try {
          const response = await authService.refreshToken(token)
          set({ token: response.token })
        } catch (error) {
          get().logout()
          throw error
        }
      },
      
      updateUser: (userData) => {
        const { user } = get()
        if (user) {
          set({ user: { ...user, ...userData } })
        }
      }
    }),
    {
      name: 'auth-store'
    }
  )
)
```

### API客户端规范
```typescript
// lib/api.ts
import { toast } from 'react-hot-toast'

class APIClient {
  private baseURL: string
  private token: string | null = null
  
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }
  
  setToken(token: string | null) {
    this.token = token
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    }
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new APIError(
          errorData.message || `HTTP ${response.status}`,
          response.status,
          errorData
        )
      }
      
      return await response.json()
    } catch (error) {
      if (error instanceof APIError) {
        throw error
      }
      
      throw new APIError('Network error', 0, { originalError: error })
    }
  }
  
  // HTTP方法封装
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(endpoint, this.baseURL)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }
    
    return this.request<T>(url.pathname + url.search)
  }
  
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }
  
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }
  
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }
}

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

export const apiClient = new APIClient()

// 服务封装示例
export const userService = {
  getAll: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<User[]>('/users', params),
    
  getById: (id: string) =>
    apiClient.get<User>(`/users/${id}`),
    
  create: (userData: CreateUserRequest) =>
    apiClient.post<User>('/users', userData),
    
  update: (id: string, userData: UpdateUserRequest) =>
    apiClient.put<User>(`/users/${id}`, userData),
    
  delete: (id: string) =>
    apiClient.delete(`/users/${id}`),
}
```

### Tailwind CSS 约定
```typescript
// 使用 utility classes 保持一致性
const buttonStyles = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-2 focus:ring-gray-500',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-2 focus:ring-red-500',
}

// 响应式设计
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 内容 */}
</div>

// 状态样式
<button
  className={clsx(
    'base-button-styles',
    {
      'opacity-50 cursor-not-allowed': disabled,
      'ring-2 ring-blue-500': focused,
    }
  )}
>
  Button text
</button>
```

## 通用规范

### Git提交信息
```bash
# 格式: <type>(<scope>): <description>
feat(api): add data source creation endpoint
fix(frontend): resolve user authentication issue
docs(readme): update installation instructions
style(backend): format code with black
refactor(database): optimize query performance
test(api): add unit tests for user service
chore(deps): update fastapi to version 0.111.0
```

### 文件和目录命名
```
# 后端文件命名
user_service.py          # 服务类
user_model.py           # 数据模型
user_schema.py          # Pydantic模式
test_user_service.py    # 测试文件

# 前端文件命名
UserService.ts          # 服务类
UserModel.ts           # 类型定义
UserList.tsx           # 组件文件
useUserStore.ts        # Hook文件
user.test.ts           # 测试文件
```

### 安全规范
1. **永远不要**在代码中硬编码API密钥或敏感信息
2. **所有**数据库查询必须包含tenant_id过滤
3. **必须**验证和清理所有用户输入
4. **必须**使用HTTPS传输敏感数据
5. **必须**设置适当的CORS策略

### 性能规范
1. **数据库查询**: 使用索引，避免N+1查询
2. **前端**: 使用React.memo和useMemo优化渲染
3. **API**: 实现分页和字段选择
4. **缓存**: 合理使用Redis缓存热点数据