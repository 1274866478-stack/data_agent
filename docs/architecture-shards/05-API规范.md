# Data Agent V4 - 第5部分：API 规范

OpenAPI 3.0 规范，已更新以支持 V4 SaaS 需求。

## 基础信息

```yaml
openapi: 3.0.0
info:
  title: "Data Agent V4 API (SaaS MVP)"
  version: "4.0.0"
servers:
  - url: "http://localhost:8004/api/v1"
```

## 认证

**V4 SaaS 认证**：使用托管认证 (Clerk/Auth0) 的 JWT

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: "JWT"

security:
  - BearerAuth: [] # 所有端点都需要 JWT
```

## 核心端点

### 1. /query (POST)

**用途**: V3 核心查询端点 (租户隔离版)

**描述**: 接收自然语言查询，在当前登录租户的上下文中返回 V3 融合答案 (含 XAI Log)

**请求体**:
```json
{
  "question": "上个季度销售额最高的笔记本电脑型号是什么？并附上它的产品介绍摘要。"
}
```

**响应**:
```json
{
  "answer": "**VisionBook Pro X15**\n\n| 季度 | 总收入 |\n|:---|---:|\n| 2025-Q2 | 1,250,000 |\n\n**产品介绍摘要:**...",
  "citations": [
    {
      "source_type": "database",
      "file_name": "product_sales",
      "page_number": 0
    }
  ],
  "explainability_log": "我选择了 `product_sales` 表，因为查询包含'销售额'..."
}
```

### 2. /data-sources/database (POST)

**用途**: V4 新增：连接外部数据库

**描述**: 为当前租户注册一个新的 PostgreSQL 数据库连接字符串

**请求体**:
```json
{
  "name": "我的生产数据库",
  "connection_string": "postgresql://user:pass@host:port/db"
}
```

### 3. /data-sources/document (POST)

**用途**: V4 新增：上传知识库文档

**描述**: 为当前租户上传一个 PDF 或 Word 文档到 MinIO

**请求体**: multipart/form-data (文件上传)

## 错误响应

- **401**: 认证失败 (无效或缺失 JWT)
- **404**: 租户数据源未找到
- **429**: 达到 Zhipu API 速率限制

---
**分片索引**: 05-API规范.md | **总页数**: 5/17