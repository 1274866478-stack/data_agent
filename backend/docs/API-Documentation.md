# Data Agent V4 - API文档

## 📚 文档访问

### Swagger UI (推荐)
交互式API文档,支持在线测试API:

**URL:** `http://localhost:8004/docs`

**功能:**
- ✅ 查看所有API端点
- ✅ 查看请求/响应模型
- ✅ 在线测试API (Try it out)
- ✅ 查看示例请求和响应
- ✅ JWT认证支持

### ReDoc
美观的API文档,适合阅读:

**URL:** `http://localhost:8004/redoc`

**功能:**
- ✅ 清晰的文档结构
- ✅ 搜索功能
- ✅ 代码示例
- ✅ 响应式设计

### OpenAPI Schema
原始OpenAPI 3.0规范:

**URL:** `http://localhost:8004/openapi.json`

---

## 🔐 认证

所有API端点(除了`/health`和`/`)都需要JWT认证。

### 获取JWT Token

1. 通过Clerk认证服务登录
2. 获取JWT token
3. 在API请求中包含token

### 使用Token

**请求头:**
```http
Authorization: Bearer <your_jwt_token>
```

**Swagger UI中使用:**
1. 点击页面右上角的 "Authorize" 按钮
2. 输入: `Bearer <your_jwt_token>`
3. 点击 "Authorize"
4. 现在可以测试需要认证的API

---

## 📋 API端点概览

### 1. 健康检查
- `GET /health` - 检查所有服务状态

### 2. 租户管理
- `GET /api/v1/tenants/me` - 获取当前租户信息
- `PUT /api/v1/tenants/me` - 更新当前租户信息
- `GET /api/v1/tenants/stats` - 获取租户统计信息

### 3. 数据源管理
- `GET /api/v1/data-sources` - 获取数据源列表
- `POST /api/v1/data-sources` - 创建数据源
- `GET /api/v1/data-sources/{id}` - 获取数据源详情
- `PUT /api/v1/data-sources/{id}` - 更新数据源
- `DELETE /api/v1/data-sources/{id}` - 删除数据源
- `POST /api/v1/data-sources/test` - 测试数据源连接

### 4. 文档管理
- `GET /api/v1/documents` - 获取文档列表
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/{id}` - 获取文档详情
- `DELETE /api/v1/documents/{id}` - 删除文档
- `POST /api/v1/documents/{id}/process` - 处理文档(向量化)

### 5. AI对话
- `POST /api/v1/llm/chat` - AI对话
- `POST /api/v1/llm/analyze` - 数据分析

---

## 📖 使用示例

### 示例1: 获取租户信息

**请求:**
```bash
curl -X GET "http://localhost:8004/api/v1/tenants/me" \
  -H "Authorization: Bearer <your_jwt_token>"
```

**响应:**
```json
{
  "id": "user_2abc123def456",
  "email": "user@example.com",
  "status": "active",
  "display_name": "张三",
  "settings": {
    "timezone": "Asia/Shanghai",
    "language": "zh-CN"
  },
  "storage_quota_mb": 1024,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T12:30:00Z"
}
```

### 示例2: 创建数据源

**请求:**
```bash
curl -X POST "http://localhost:8004/api/v1/data-sources" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "生产数据库",
    "db_type": "postgresql",
    "connection_string": "postgresql://user:password@localhost:5432/mydb"
  }'
```

**响应:**
```json
{
  "id": "ds_abc123",
  "tenant_id": "user_2abc123def456",
  "name": "生产数据库",
  "db_type": "postgresql",
  "status": "active",
  "created_at": "2025-01-15T12:00:00Z"
}
```

### 示例3: 上传文档

**请求:**
```bash
curl -X POST "http://localhost:8004/api/v1/documents/upload" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -F "file=@document.pdf"
```

**响应:**
```json
{
  "id": "doc_xyz789",
  "tenant_id": "user_2abc123def456",
  "filename": "document.pdf",
  "file_size": 2048576,
  "file_type": "application/pdf",
  "status": "uploaded",
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

## 🔧 开发工具

### Postman Collection
导入OpenAPI规范到Postman:
1. 打开Postman
2. Import → Link → 输入 `http://localhost:8004/openapi.json`
3. 配置环境变量 (base_url, jwt_token)

### HTTPie
```bash
# 安装HTTPie
pip install httpie

# 使用示例
http GET http://localhost:8004/api/v1/tenants/me \
  Authorization:"Bearer <token>"
```

---

## 📝 错误处理

### 常见错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 200 | 成功 | 请求成功处理 |
| 201 | 创建成功 | 资源创建成功 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未认证 | JWT token无效或缺失 |
| 403 | 无权限 | 租户隔离验证失败 |
| 404 | 未找到 | 资源不存在 |
| 422 | 验证错误 | 请求体验证失败 |
| 500 | 服务器错误 | 内部错误 |

### 错误响应格式

```json
{
  "error": "Validation Error",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "timestamp": "2025-01-15T12:30:00Z"
}
```

---

**最后更新:** 2025-11-17

