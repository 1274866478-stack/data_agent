# Data Agent V4 - 问题修复日志

**项目**: Data Agent V4 - 多租户SaaS数据智能分析平台
**维护者**: AI Assistant
**最后更新**: 2025-11-30

---

## 问题修复记录

---

### BUG-020: 前端页面"无法访问此网络"错误 - API请求路径错误

**发现时间**: 2025-11-27
**严重程度**: 🔴 高 (阻塞性)
**状态**: ✅ 已修复

#### 问题描述
用户访问前端页面时显示"无法访问此网络"的错误页面。浏览器控制台显示 404 错误：
```
GET /api/v1/data-sources/overview 404 (Not Found)
GET /api/v1/data-sources/search?q=&type=databases&page=1&limit=20 404 (Not Found)
```

#### 根本原因
**问题代码位置**: `frontend/src/store/dashboardStore.ts`

在 `dashboardStore.ts` 中，`fetchOverview`、`searchDataSources` 和 `bulkDelete` 函数直接使用相对路径 `/api/v1/...` 发送 fetch 请求：

```typescript
// ❌ 错误的写法 - 请求发送到前端的 Next.js 服务器
const response = await fetch('/api/v1/data-sources/overview', ...)
const response = await fetch('/api/v1/data-sources/search?${params}', ...)
const response = await fetch('/api/v1/data-sources/bulk-delete', ...)
```

这导致请求被发送到前端的 Next.js 服务器（`localhost:3000`），而不是后端 FastAPI 服务器（`localhost:8004`）。

#### 解决方法

**步骤1**: 添加 API 基础 URL 获取函数

在 `dashboardStore.ts` 文件开头添加：
```typescript
// 获取 API 基础 URL
const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
}
```

**步骤2**: 修改所有 fetch 请求使用完整 URL

```typescript
// ✅ 正确的写法 - 请求发送到后端 FastAPI 服务器
const apiBaseUrl = getApiBaseUrl()
const response = await fetch(`${apiBaseUrl}/data-sources/overview`, ...)
const response = await fetch(`${apiBaseUrl}/data-sources/search?${params}`, ...)
const response = await fetch(`${apiBaseUrl}/data-sources/bulk-delete`, ...)
```

#### 修改的文件
1. `frontend/src/store/dashboardStore.ts` - 修复 API 请求路径（4处修改）

#### 环境配置
确保 `frontend/.env.local` 文件包含正确的 API URL：
```
NEXT_PUBLIC_API_URL=http://localhost:8004/api/v1
```

#### 预防措施

**开发规范**:
1. ⚠️ **永远不要在前端使用相对路径调用后端 API** - 因为前端和后端运行在不同端口
2. ✅ **始终使用环境变量配置 API 基础 URL** - 便于不同环境的切换
3. ✅ **在 store 或 service 文件中统一管理 API 调用** - 便于维护和调试
4. ✅ **参考 `api-client.ts` 的实现模式** - 该文件已正确使用 `NEXT_PUBLIC_API_URL`

**正确示例** (`frontend/src/lib/api-client.ts`):
```typescript
export class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }
  
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    // ...
  }
}
```

**错误示例** (避免):
```typescript
// ❌ 错误 - 相对路径会发送到前端服务器
fetch('/api/v1/data-sources')

// ✅ 正确 - 使用完整 URL 发送到后端服务器
fetch(`${process.env.NEXT_PUBLIC_API_URL}/data-sources`)
```

#### 验证
- ✅ 前端服务启动正常（端口 3000）
- ✅ 后端服务启动正常（端口 8004）
- ✅ API 请求正确发送到后端服务器
- ✅ 页面正常加载，不再显示 404 错误

---

### BUG-021: 数据源管理页面 "加载概览数据失败: Failed to fetch" 错误

**发现时间**: 2025-11-28
**严重程度**: 🔴 高 (阻塞性)
**状态**: ✅ 已修复

#### 问题描述
用户访问数据源管理页面 (`/data-sources`) 时显示错误提示 "加载概览数据失败: Failed to fetch"。浏览器控制台显示多个错误：
- `403 Forbidden` - Invalid or inactive tenant
- `500 Internal Server Error` - Search operation failed
- CORS 策略阻止跨域请求

#### 根本原因
该问题由多个因素组成：

**问题1: FastAPI 路由顺序错误**
- **位置**: `backend/src/app/api/v1/endpoints/data_sources.py`
- **原因**: 动态路由 `/{connection_id}` 定义在固定路由 `/overview`、`/search` 之前，导致 FastAPI 将 `overview` 和 `search` 误识别为 `connection_id` 参数

**问题2: 变量遮蔽**
- **位置**: `backend/src/app/api/v1/endpoints/data_sources.py` 第 166 行
- **原因**: `search_data_sources_route` 函数的 `status` 参数遮蔽了从 FastAPI 导入的 `status` 模块

**问题3: Tenant 模型字段引用错误**
- **位置**: `backend/src/app/api/v1/endpoints/data_sources.py` 多处
- **原因**: 代码使用 `Tenant.is_active == True`，但 `Tenant` 模型实际使用 `status` 字段（枚举类型）

**问题4: 前端缺少租户参数**
- **位置**: `frontend/src/store/dashboardStore.ts`
- **原因**: API 请求未传递 `tenant_id` 和 `user_id` 参数

**问题5: 前端类型名称不匹配**
- **位置**: `frontend/src/store/dashboardStore.ts`
- **原因**: 前端发送 `type=databases`，后端期望 `type=database`

**问题6: 开发租户不存在**
- **原因**: 前端开发模式使用的模拟租户 `dev-tenant-001` 在数据库中不存在

#### 解决方法

**修复1: 调整路由顺序**
将固定路径端点移动到动态路径之前：
```python
# ✅ 正确顺序 - 固定路径在前
@router.get("/overview", ...)
@router.get("/search", ...)
@router.post("/bulk-delete", ...)
@router.get("/types/supported", ...)

# 动态路径在后
@router.get("/{connection_id}", ...)
```

**修复2: 重命名参数避免遮蔽**
```python
# ❌ 错误
async def search_data_sources_route(status: Optional[str] = None, ...):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, ...)  # status 被遮蔽

# ✅ 正确
async def search_data_sources_route(status_filter: Optional[str] = None, ...):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, ...)
```

**修复3: 修正 Tenant 字段引用**
```python
from ..data.models import TenantStatus

# ❌ 错误 - is_active 字段不存在
tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()

# ✅ 正确 - 使用 status 枚举字段
tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.status == TenantStatus.ACTIVE).first()
```

**修复4: 添加租户参数到前端请求**
```typescript
// 添加 helper 函数获取认证参数
const getAuthParams = () => {
  const user = useAuthStore.getState().user
  return {
    tenant_id: user?.tenant_id || 'default_tenant',
    user_id: user?.id || 'anonymous'
  }
}

// 在 API 请求中使用
const { tenant_id, user_id } = getAuthParams()
const params = new URLSearchParams({ tenant_id, user_id })
const response = await fetch(`${apiBaseUrl}/data-sources/overview?${params}`, ...)
```

**修复5: 映射类型名称**
```typescript
// 将前端 tab 名称映射到后端期望的类型
const tabToType: Record<string, string> = {
  'databases': 'database',
  'documents': 'document'
}
const searchType = filters.type === 'all'
  ? (tabToType[activeTab] || activeTab)
  : filters.type
```

**修复6: 创建开发租户**
```bash
curl -X POST "http://localhost:8004/api/v1/tenants/setup" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "dev-tenant-001", "email": "dev@dataagent.local", "display_name": "Development Tenant"}'
```

#### 修改的文件
1. `backend/src/app/api/v1/endpoints/data_sources.py` - 修复路由顺序、变量遮蔽、Tenant 字段引用
2. `frontend/src/store/dashboardStore.ts` - 添加租户参数、修复类型映射

#### 预防措施

**后端开发规范**:
1. ⚠️ **FastAPI 路由顺序**: 固定路径必须定义在动态路径参数之前
2. ⚠️ **避免变量遮蔽**: 函数参数名不要与导入模块同名
3. ✅ **使用正确的模型字段**: 修改前先确认模型定义

**前端开发规范**:
1. ✅ **多租户 API 调用必须传递 tenant_id 和 user_id**
2. ✅ **确保前后端参数命名一致**

**Tenant 模型参考**:
```python
class Tenant(Base):
    id = Column(String(255), primary_key=True)  # 支持 Clerk user ID
    email = Column(String(255), unique=True, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE)  # 使用枚举
    display_name = Column(String(255))
    storage_quota_mb = Column(Integer, default=1024)
    # 注意：没有 is_active、max_documents、max_data_sources 字段
```

#### 验证
- ✅ 后端 `/api/v1/data-sources/overview` 端点正常返回数据
- ✅ 后端 `/api/v1/data-sources/search` 端点正常返回数据
- ✅ 前端页面正常加载，无控制台错误
- ✅ 数据源概览和搜索功能正常工作

---

### BUG-022: 数据源删除后刷新页面仍然显示 - 软删除与前端筛选问题

**发现时间**: 2025-11-30
**严重程度**: 🟡 中 (用户体验问题)
**状态**: ✅ 已修复

#### 问题描述
用户在前端删除数据源后,刷新页面时已删除的数据源仍然显示在列表中。用户多次删除同一数据源,但每次刷新后都会重新出现。

#### 根本原因
该问题由两个因素组成:

**问题1: 软删除机制**
- **位置**: `backend/src/app/api/v1/endpoints/data_sources.py` - `delete_data_source` 和 `bulk_delete_data_sources_route` 函数
- **原因**: 删除操作只是将数据源状态设置为 `INACTIVE`,而不是真正从数据库中删除记录

```python
# 软删除实现
connection.status = DataSourceConnectionStatus.INACTIVE
connection.updated_at = datetime.now()
db.commit()
```

**问题2: 前端默认筛选显示所有状态**
- **位置**: `frontend/src/components/data-sources/DataSourceList.tsx` 第 32 行
- **原因**: 前端默认 `filterStatus = 'all'`,导致获取数据源时 `active_only = false`,包括 `INACTIVE` 状态的数据源

```typescript
// ❌ 问题代码
const [filterStatus, setFilterStatus] = useState<string>('all')

// 在 fetchDataSources 调用中
fetchDataSources(tenantId, {
  active_only: filterStatus !== 'all',  // 'all' 时为 false,显示所有状态
})
```

**问题3: 后端筛选逻辑**
- **位置**: `backend/src/app/services/data_source_service.py` 第 142-143 行
- **逻辑**: 当 `active_only = false` 时,不过滤 `INACTIVE` 状态的数据源

```python
if active_only:
    query = query.filter(DataSourceConnection.status != DataSourceConnectionStatus.INACTIVE)
# 如果 active_only = false,则不过滤,返回所有状态包括 INACTIVE
```

#### 解决方法

**修复1: 修改前端默认筛选为只显示活跃数据源**

```typescript
// ✅ 修复后 - 默认只显示活跃的数据源
const [filterStatus, setFilterStatus] = useState<string>('active')
```

**文件**: `frontend/src/components/data-sources/DataSourceList.tsx` 第 32 行

**修复2: 清理数据库中的 INACTIVE 数据源(可选)**

如果需要彻底删除已标记为 `INACTIVE` 的数据源:

```sql
DELETE FROM data_source_connections WHERE status = 'INACTIVE';
```

执行结果: 删除了 4 条 INACTIVE 记录

#### 数据库状态对比

**修复前**:
```
id                                  | name             | db_type    | status   | tenant_id
------------------------------------+------------------+------------+----------+----------------
b3d3b217-3eae-4807-91d6-5c3090a3e1b2| 测试数据库       | postgresql | ERROR    | dev-tenant-001
9948e3de-382d-486c-a337-965300d7f949| 测试数据库       | postgresql | INACTIVE | dev-tenant-001
5de0bf75-71cb-4c38-b958-a6f1057ba729| ChatBI测试数据库 | postgresql | ACTIVE   | default_tenant
c5610522-b8eb-49cd-889f-ecd50883f5c0| chatbi_test_data | xlsx       | INACTIVE | dev-tenant-001
60e2fade-3a06-465e-ae3a-3ce646eba3f1| chatbi_test      | db         | INACTIVE | dev-tenant-001
3d188aa0-83a4-412d-8aa3-18569ce66d66| chatbi_test      | db         | INACTIVE | dev-tenant-001
```

**修复后**:
```
id                                  | name             | db_type    | status | tenant_id
------------------------------------+------------------+------------+--------+----------------
b3d3b217-3eae-4807-91d6-5c3090a3e1b2| 测试数据库       | postgresql | ERROR  | dev-tenant-001
5de0bf75-71cb-4c38-b958-a6f1057ba729| ChatBI测试数据库 | postgresql | ACTIVE | default_tenant
```

#### 修改的文件
1. `frontend/src/components/data-sources/DataSourceList.tsx` - 修改默认筛选状态从 `'all'` 到 `'active'`

#### 用户体验改进

**修复前**:
- 用户删除数据源后,刷新页面仍然看到已删除的数据源
- 需要手动切换筛选器到"已连接"才能隐藏已删除的数据源
- 造成困惑,用户不确定删除是否成功

**修复后**:
- 默认只显示活跃的数据源(状态为 `ACTIVE`, `TESTING`, `ERROR`)
- 已删除的数据源(`INACTIVE`)不再显示
- 用户可以通过筛选器选择"所有状态"来查看包括已删除的数据源
- 删除操作的反馈更加直观

#### 预防措施

**前端开发规范**:
1. ✅ **默认筛选应该符合用户预期** - 大多数情况下用户只想看到活跃的数据
2. ✅ **提供筛选选项让用户查看所有状态** - 保留灵活性
3. ✅ **删除操作后自动刷新列表** - 确保UI与数据库状态同步

**后端开发规范**:
1. ✅ **软删除是推荐的做法** - 保留数据用于审计和恢复
2. ✅ **提供 `active_only` 参数** - 让前端控制是否显示已删除的数据
3. ✅ **考虑添加硬删除API** - 用于管理员彻底清理数据

**数据源状态枚举**:
```python
class DataSourceConnectionStatus(str, Enum):
    TESTING = "TESTING"      # 正在测试连接
    ACTIVE = "ACTIVE"        # 已连接(绿色)
    ERROR = "ERROR"          # 连接错误(红色)
    INACTIVE = "INACTIVE"    # 已删除/未激活(灰色,默认不显示)
```

#### 相关问题

**连接字符串加密问题** (同时修复):
- **问题**: 创建数据源时报错 "Connection string cannot be empty"
- **原因**: 后端先创建 `DataSourceConnection` 对象时设置 `connection_string=""`,然后尝试赋值加密字符串,触发 setter 验证
- **修复**: 先加密连接字符串,然后直接赋值到私有字段 `_connection_string`,绕过 setter 验证

```python
# ❌ 错误的实现
new_connection = DataSourceConnection(
    connection_string="",  # 空字符串
    status=DataSourceConnectionStatus.TESTING
)
encrypted_string = encryption_service.encrypt_connection_string(request.connection_string)
new_connection.connection_string = encrypted_string  # 触发 setter 验证失败

# ✅ 正确的实现
encrypted_string = encryption_service.encrypt_connection_string(request.connection_string)
new_connection = DataSourceConnection(
    _connection_string=encrypted_string,  # 直接设置私有字段
    status=DataSourceConnectionStatus.TESTING
)
```

**自动测试连接** (同时添加):
- **改进**: 创建数据源后自动测试连接并更新状态
- **好处**: 用户无需手动点击"测试连接",状态自动从 `TESTING` 变为 `ACTIVE` 或 `ERROR`

```python
# 自动测试连接并更新状态
try:
    test_result = await connection_test_service.test_connection(
        connection_string=request.connection_string,
        db_type=request.db_type
    )
    new_connection.update_test_result(test_result.to_dict())
    db.commit()
except Exception as e:
    logger.warning(f"Auto-test failed: {e}")
```

#### 验证
- ✅ 前端默认只显示活跃的数据源
- ✅ 删除数据源后刷新页面不再显示
- ✅ 用户可以通过筛选器选择"所有状态"查看已删除的数据源
- ✅ 创建数据源时连接字符串正确加密
- ✅ 创建数据源后自动测试连接并更新状态

---

## 相关配置

### 服务端口配置
| 服务 | 端口 | 描述 |
|------|------|------|
| 前端 (Next.js) | 3000 | 前端应用 |
| 后端 (FastAPI) | 8004 | 后端 API |
| PostgreSQL | 5432 | 主数据库 |
| MinIO | 9000/9001 | 对象存储 |
| ChromaDB | 8001 | 向量数据库 |

### 环境变量
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8004/api/v1
```

---

**注意**: 本日志记录了项目开发过程中遇到的关键问题和解决方案，请开发人员参考并避免重复出现类似问题。

