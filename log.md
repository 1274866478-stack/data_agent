# Data Agent V4 - 问题修复日志

**项目**: Data Agent V4 - 多租户SaaS数据智能分析平台
**维护者**: AI Assistant
**最后更新**: 2025-11-27

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

