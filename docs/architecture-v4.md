# Data Agent V4 - 全栈架构文档 (SaaS MVP)

**版本**: 4.0 (Zhipu 版)  
**日期**: 2025年11月16日  
**架构师**: Winston (BMad)  
**基于**: PRD V4 (SaaS MVP - Zhipu 版)

---

## 变更日志 (Change Log)

| 日期 | 版本 | 描述 | 作者 |
|:---|:---|:---|:---|
| 2025-11-15 | 4.0 | 基于 PRD V4 (SaaS MVP - Zhipu 版) 创建 | Winston |
| 2025-11-16 | 4.0 | 合并所有架构文档和分片到统一V4版本 | Winston |

---

## 第 1 部分: 引言 (Introduction)

### 项目概述

本文件概述了 **Data Agent V4 (SaaS MVP)** 的完整全栈架构。其目标是在本地通过 **Docker Compose** 运行一个**云就绪 (Cloud-Ready)** 的**多租户**平台，以验证**"用户自带数据 (BYO-Data)"** 的核心循环。

### 启动模板 (Starter Template)

**N/A - Greenfield project (绿地项目)**。我们将根据 PRD V4 定义的 Docker、FastAPI 和 Next.js 结构从零开始构建。

---

## 第 2 部分: 高层架构 (High Level Architecture)

### 技术摘要 (Technical Summary)

本架构是一个**云就绪 (Cloud-Ready)**、**多租户 (Multi-Tenant)** 的全栈应用，通过 **Docker Compose** 在本地运行。前端采用 **Next.js** ("the curator." 风格)，后端采用 **FastAPI**。认证(例如 Clerk)处理用户和租户身份。Agentic Core 将使用 **Zhipu GLM API**(替代 DeepSeek)，并根据租户 ID 查询其自备的 **PostgreSQL**(通过连接字符串导入)和 **MinIO**(用于文档上传)。

### 平台与基础设施选择 (Platform and Infrastructure Choice)

**平台 (MVP)**: Docker Compose

**理由 (Rationale)**: 满足 PRD V4 NFR1 和 NFR2 的要求，在本地模拟云微服务环境，确保未来可以平滑迁移到云服务器。

**关键服务 (Docker Compose)**:
- `frontend` (Next.js)
- `backend` (FastAPI)
- `db` (PostgreSQL)
- `storage` (MinIO)
- `vector_db` (ChromaDB)

### 代码仓库结构 (Repository Structure)

**结构 (Structure)**: Monorepo (单一仓库)，由 `docker-compose.yml` 在根目录编排。

### 高层架构图 (Architecture Diagram)

```mermaid
graph TD
    subgraph "用户 (浏览器)"
        U(租户 A/B/C)
    end

    U -- "登录" --> Auth(Clerk/Auth0)
    Auth -- "JWT (含 tenant_id)" --> U
    U -- "访问 (JWT)" --> FE_App(1. 前端 Next.js<br/>style.md UI)

    subgraph "本地 Docker Compose 环境"
        FE_App -- "POST /api/v1/query JWT" --> API_GW(2. 后端 FastAPI<br/>JWT 验证)

        API_GW -- "tenant_id, question" --> Agent_Core(3. V3 Agentic Core<br/>租户隔离)

        Agent_Core -- "调用" --> SQL_Chain(RAG-SQL 链)
        SQL_Chain -- "查询 tenant_id" --> DB_Tenant(4. PostgreSQL<br/>存储租户连接字符串)

        Agent_Core -- "调用" --> RAG_Chain(RAG 链)
        RAG_Chain -- "检索 tenant_id" --> VDB(5. ChromaDB)

        RAG_Chain -- "获取文档" --> Storage(6. MinIO)

        SQL_Chain -- "SQL 结果" --> Fusion(XAI 融合)
        RAG_Chain -- "文档数据" --> Fusion
        Fusion -- "融合答案 + XAI Log" --> Agent_Core

        Agent_Core -- "响应" --> API_GW
        API_GW -- "200 OK V3 响应" --> FE_App
    end

    subgraph "外部 API"
        Agent_Core -- "LLM 调用" --> Zhipu(Zhipu GLM API)
    end
```

### 架构模式 (Architectural Patterns)

- **多租户 SaaS (Multi-Tenant SaaS)**: V4 的核心。认证和数据访问必须与租户 ID 绑定。
- **自带数据 (BYO-Data)**: 系统不托管用户的核心结构化数据，而是安全地存储连接字符串并远程查询。
- **Agentic RAG-SQL**: (V3 保留) 保留 Agentic Core、自我修正和 XAI 逻辑。
- **云就绪 (Cloud-Ready)**: 使用 Docker Compose 确保本地 MVP 与生产环境(云服务器)一致。

---

## 第 3 部分: 技术栈 (Tech Stack)

PRD V4 权威技术选型。

| 类别 | 技术选型 | 版本 | 用途 |
|:---|:---|:---|:---|
| 前端框架 | Next.js | 14+ | JS 框架 |
| UI 组件库 | shadcn/ui | 最新版 | UI 框架 ("the curator." 风格) |
| 后端框架 | FastAPI | 最新版 | 后端框架 |
| AI/LLM 框架 | LangChain / LangGraph | 最新版 | AI/LLM 框架 |
| LLM API (V4) | Zhipu (智谱) API (GLM) | glm-4 | 大语言模型 |
| 数据库 (V4) | PostgreSQL | 16+ (Docker) | 租户元数据和用户数据库 |
| 向量数据库 | ChromaDB | (Docker) | 向量存储 (租户隔离) |
| 对象存储 (V4) | MinIO | (Docker) | 存储用户上传的文档 |
| 认证 (V4) | Clerk / Auth0 | (SaaS) | 多租户用户认证 |
| 部署 (MVP) | Docker Compose | | 本地云模拟 |

---

## 第 4 部分: 数据模型 (Data Models)

V4 数据模型(存储在 Docker PostgreSQL 中)必须支持多租户。

### 数据模型 1: Tenant (V4 新增)

**用途**: 存储租户(组织/用户)信息。

**TypeScript 接口 (共享)**:

```typescript
export interface Tenant {
  id: string; // (来自 Clerk/Auth0 的 User/Org ID)
  email: string;
  createdAt: string;
}
```

### 数据模型 2: DataSourceConnection (V4 新增)

**用途**: 安全地存储用户导入的数据库连接字符串。

**TypeScript 接口 (共享)**:

```typescript
export interface DataSourceConnection {
  id: string;
  tenant_id: string; // (外键 -> Tenant.id)
  db_type: 'postgresql'; // MVP 仅支持 PG
  connection_string: string; // (必须在数据库中加密存储)
  name: string;
  createdAt: string;
}
```

### 数据模型 3: KnowledgeDocument (V4 新增)

**用途**: 跟踪用户上传的文档。

**TypeScript 接口 (共享)**:

```typescript
export interface KnowledgeDocument {
  id: string;
  tenant_id: string; // (外键 -> Tenant.id)
  file_name: string; // (例如 'annual_report.pdf')
  storage_path: string; // (例如 'tenant-abc/annual_report.pdf')
  status: 'PENDING' | 'INDEXING' | 'READY';
  createdAt: string;
}
```

### 数据模型 4: KnowledgeCitation (V3 修改版)

**用途**: API 响应中的溯源格式。

**TypeScript 接口 (共享)**:

```typescript
export interface KnowledgeCitation {
  source_type: 'database' | 'pdf' | 'docx'; // (V4 MVP 降级：移除 v3_chart_table)
  file_name: string; // (例如 'product_sales' 或 'annual_report.pdf')
  page_number?: number;
}
```

### 多租户数据隔离策略

- **数据库级别分离**: 每个租户独立的 schema (可选)
- **行级别安全**: RLS (Row Level Security) 策略
- **应用层隔离**: 基于租户 ID 的数据过滤 (V4 核心实现)

---

## 第 5 部分: API 规范 (API Specification)

OpenAPI 3.0 规范，已更新以支持 V4 SaaS 需求。

```yaml
openapi: 3.0.0
info:
  title: "Data Agent V4 API (SaaS MVP)"
  version: "4.0.0"
servers:
  - url: "http://localhost:8004/api/v1" # (Docker 内部端口 8000，映射到 8004)

# V4 (SaaS) 认证：使用托管认证 (Clerk/Auth0) 的 JWT
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: "JWT" # (V4 升级：从 API 密钥升级)

security:
  - BearerAuth: [] # 所有端点都需要 JWT

paths:
  /query:
    post:
      summary: "V3 核心查询端点 (租户隔离版)"
      description: "接收自然语言查询，在当前登录租户的上下文中返回 V3 融合答案 (含 XAI Log)"
      requestBody:
        $ref: "#/components/schemas/QueryRequest"
      responses:
        "200":
          $ref: "#/components/schemas/QueryResponseV3"
        "401":
          description: "认证失败 (无效或缺失 JWT)"
        "404":
          description: "租户数据源未找到"
        "429":
          description: "达到 Zhipu API 速率限制"

  /data-sources/database:
    post:
      summary: "V4 新增：连接外部数据库"
      description: "为当前租户注册一个新的 PostgreSQL 数据库连接字符串。"
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                  example: "我的生产数据库"
                connection_string:
                  type: string
                  example: "postgresql://user:pass@host:port/db"
      responses:
        "201":
          description: "数据源连接成功"
        "400":
          description: "连接字符串无效"

  /data-sources/document:
    post:
      summary: "V4 新增：上传知识库文档"
      description: "为当前租户上传一个 PDF 或 Word 文档到 MinIO。"
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
      responses:
        "201":
          description: "文档上传成功，开始索引"
        "415":
          description: "不支持的文件类型"

# 共享的数据模型/模式
components:
  schemas:
    QueryRequest:
      type: object
      properties:
        question:
          type: string
          example: "上个季度销售额最高的笔记本电脑型号是什么？并附上它的产品介绍摘要。"
      required:
        - question

    KnowledgeCitation:
      type: object
      properties:
        source_type:
          type: string
          enum: [database, pdf, docx]
          example: "database"
        file_name:
          type: string
          example: "product_sales"
        page_number:
          type: integer
          example: 0
      required:
        - source_type
        - file_name

    QueryResponseV3:
      type: object
      properties:
        answer:
          type: string
          description: "V3 融合答案 (Markdown 格式)"
          example: "**VisionBook Pro X15**\n\n| 季度 | 总收入 |\n|:---|---:|\n| 2025-Q2 | 1,250,000 |\n\n**产品介绍摘要:**..."
        citations:
          type: array
          items:
            $ref: "#/components/schemas/KnowledgeCitation"
        explainability_log:
          type: string
          description: "V3 XAI 推理路径"
          example: "我选择了 `product_sales` 表，因为查询包含'销售额'..."
      required:
        - answer
        - citations
        - explainability_log
```

---

## 第 6 部分: 前端架构 (Frontend Architecture)

V4 变更：`frontend/src/app/` 文件夹将包含新的受保护路由和公共路由。

### 前端目录结构

```
frontend/src/app/
├── (auth)/         # (V4 新增) 公共路由 (登录/注册)
│   ├── sign-in/
│   └── sign-up/
├── (app)/          # (V4 新增) 受保护的租户应用
│   ├── layout.tsx    # (V4) 包含 Auth Provider 和 style.md 布局
│   ├── page.tsx      # (V3 保留) 聊天
│   └── data-sources/ # (V4 新增)
├── components/
└── lib/
    ├── api.ts        # (V4 更新) 必须使用 Auth JWT
    └── store.ts      # (V3 保留)
```

### API 客户端 (lib/api.ts)

`lib/api.ts` 必须被重构，以使用托管认证服务(例如 useAuth 钩子)来获取动态的 JWT Token，并将其作为 `Authorization: Bearer <JWT_TOKEN>` 发送。

**示例代码**:

```typescript
// lib/api.ts
import { useAuth } from '@clerk/nextjs'; // 或 Auth0

export async function queryAPI(question: string) {
  const { getToken } = useAuth();
  const token = await getToken();

  const response = await fetch('http://localhost:8004/api/v1/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  });

  return response.json();
}
```

### UI 规范

继续使用 **"the curator."** `style.md` 规范：
- 使用 shadcn/ui 组件
- Tailwind CSS 样式
- 简洁、现代的设计
- 响应式布局

---

## 第 7 部分: 后端架构 (Backend Architecture)

### V4 认证架构 (Authentication Architecture)

`deps.py` 必须被完全替换。新的依赖项必须从 `Authorization: Bearer <JWT_TOKEN>` 头中解码 JWT，验证它(使用 Clerk/Auth0 的公钥)，并提取 `tenant_id`。

**示例代码**:

```python
# backend/src/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os

security = HTTPBearer()

async def get_current_tenant_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    验证 JWT Token 并提取 tenant_id
    """
    try:
        token = credentials.credentials
        # 使用 Clerk/Auth0 的公钥验证 JWT
        payload = jwt.decode(
            token,
            os.getenv("AUTH_PUBLIC_KEY"),
            algorithms=["RS256"]
        )
        tenant_id = payload.get("sub")  # 或 "org_id"
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return tenant_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

### V4 租户隔离 (Tenant Isolation)

**Agentic Core**: `agent_core.py` 必须更新，接受 `tenant_id` 作为参数。

**RAG 链**: 必须在 ChromaDB 检索中添加 `where={"tenant_id": tenant_id}` 过滤器。

**RAG-SQL 链**: 必须首先从 PostgreSQL 中检索该 `tenant_id` 的数据库连接字符串，然后使用该连接字符串执行查询。

**示例代码**:

```python
# backend/src/app/services/agent_core.py
async def process_query(question: str, tenant_id: str):
    """
    租户隔离的查询处理
    """
    # 1. 获取租户的数据源连接
    db_connection = await get_tenant_db_connection(tenant_id)

    # 2. RAG-SQL 链 (使用租户的数据库)
    sql_result = await rag_sql_chain(question, db_connection)

    # 3. RAG 链 (使用租户的向量数据)
    rag_result = await rag_chain(question, tenant_id)

    # 4. XAI 融合
    final_answer = await fusion_engine(sql_result, rag_result)

    return final_answer
```

---

## 第 8 部分: 统一项目结构 (Unified Project Structure)

```
/Data-Agent-V4/
├── backend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── deps.py       # (V4 更新) JWT 租户验证
│   │   │   │   └── v1/
│   │   │   │       ├── router.py
│   │   │   │       ├── query.py    # (V4 更新) 租户隔离的 /query
│   │   │   │       └── data_source.py # (V4 新增) /data-sources/* 路由
│   │   │   ├── core/
│   │   │   ├── services/         # (V4 更新) 租户隔离的 Agentic Core
│   │   │   ├── data/           # (V4 更新) PostgreSQL 和 ChromaDB
│   │   │   ├── schemas.py      # (V4 更新) 包含租户模式
│   │   │   └── main.py
│   ├── .env                    # (V4 更新) 包含 ZHIPUAI_API_KEY, DB_URL, MINIO_KEY
│   ├── Dockerfile              # (V4 新增)
│   └── requirements.txt        # (V4 更新) 包含 zhipuai, psycopg2, minio
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/         # (V4 新增) 登录路由
│   │   │   ├── (app)/          # (V4 新增) 受保护路由
│   │   │   │   ├── page.tsx      # (V3 保留) 聊天
│   │   │   │   └── data-sources/ # (V4 新增)
│   │   │   └── layout.tsx    # (V4 更新) 包含 Auth Provider
│   ├── .env.local            # (V4 更新) 包含 Clerk/Auth0 密钥
│   └── Dockerfile              # (V4 新增)
├── docs/
│   ├── prd-v4.md           # (PRD V4)
│   ├── architecture-v4.md  # (本文档)
│   └── style.md            # (UI 规范)
├── docker-compose.yml        # (V4 新增) 编排 (frontend, backend, db, storage, vector_db)
└── README.md                 # (V4 更新) 包含 `docker compose up` 说明
```

---

## 第 9 部分: 开发工作流 (Development Workflow)

### (V4 升级) Local Development Setup (本地开发设置)

#### Initial Setup (初次安装)

```bash
# 1. 克隆仓库
git clone [REPO_URL] && cd Data-Agent-V4/

# 2. 复制 .env 模板
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# 3. 填入你的 ZHIPUAI_API_KEY 和 Clerk/Auth0 密钥
# 编辑 backend/.env 和 frontend/.env.local

# 4. (V4 升级) 启动整个 SaaS 环境
docker compose up --build
```

#### Docker Compose 配置示例

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8004
      - NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${CLERK_PUBLISHABLE_KEY}
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8004:8000"
    environment:
      - ZHIPUAI_API_KEY=${ZHIPUAI_API_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/dataagent
      - MINIO_ENDPOINT=storage:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    depends_on:
      - db
      - storage
      - vector_db

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=dataagent
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  storage:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  vector_db:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8000"

volumes:
  postgres_data:
  minio_data:
  chroma_data:
```

### 开发流程

1. **启动服务**: `docker compose up`
2. **查看日志**: `docker compose logs -f [service_name]`
3. **重启服务**: `docker compose restart [service_name]`
4. **停止服务**: `docker compose down`
5. **清理数据**: `docker compose down -v` (删除所有卷)

---

## 第 10 部分: 部署架构 (Deployment Architecture)

### (V4 升级) Deployment Strategy (部署策略)

#### MVP 部署 (本地)
- **平台**: Docker Compose
- **目的**: 验证功能和性能

#### 生产部署 (云服务器)

**Frontend Deployment**:
- Vercel / Netlify
- 自动 CI/CD 集成
- 全球 CDN 分发

**Backend Deployment**:
- Fly.io / AWS ECS / Google Cloud Run
- 部署 backend/ Dockerfile
- 自动扩展支持

**Database (Production)**:
- Supabase / Neon / AWS RDS (PostgreSQL)
- 自动备份
- 高可用配置

**Storage (Production)**:
- AWS S3 / Cloudflare R2
- MinIO 兼容 API
- 全球分发

**Vector Database (Production)**:
- Pinecone / Weaviate / Qdrant
- 托管服务
- 高性能检索

### 环境变量管理

**开发环境** (.env.local):
```bash
ZHIPUAI_API_KEY=your_dev_key
DATABASE_URL=postgresql://localhost:5432/dataagent_dev
```

**生产环境** (环境变量):
```bash
ZHIPUAI_API_KEY=your_prod_key
DATABASE_URL=postgresql://prod-host:5432/dataagent_prod
```

---

## 第 11 部分: 安全与性能 (Security and Performance)

### (V4 升级) Security Requirements (安全要求)

#### 认证安全
- **JWT (JSON Web Token)**: 后端 FastAPI 必须使用托管认证提供商(Clerk/Auth0)的公钥验证每个请求的 JWT
- **Token 过期**: 设置合理的过期时间(如 1 小时)
- **刷新机制**: 实现 Token 刷新流程

#### 数据隔离
- **(V4 核心)** 所有数据库查询(SQL 和 ChromaDB)必须包含一个 `WHERE tenant_id = '...'` 子句
- 该 `tenant_id` 从经过验证的 JWT 中提取
- 绝不允许跨租户数据访问

#### 凭证安全
- 用户提供的数据库连接字符串必须在存入 PostgreSQL 之前进行**加密**
- 使用专用的密钥管理服务(如 AWS KMS)
- 环境变量不应包含敏感信息的明文

#### 传输安全
- 生产环境必须使用 HTTPS/TLS 1.3
- 所有 API 调用必须加密
- 禁用不安全的协议

### Performance Optimization (性能优化)

#### 数据库优化
- **索引策略**: 在 `tenant_id` 字段上创建索引
- **查询优化**: 使用 EXPLAIN ANALYZE 分析慢查询
- **连接池**: 配置合理的数据库连接池大小

#### 缓存策略
- **Redis 缓存**: 缓存频繁查询的结果
- **TTL 设置**: 根据数据更新频率设置合理的 TTL
- **缓存失效**: 实现智能缓存失效机制

#### 异步处理
- **文档索引**: 使用 Celery 异步处理文档上传和索引
- **批量操作**: 批量处理大量数据操作
- **队列管理**: 使用 Redis 作为消息队列

---

## 第 12 部分: 测试策略 (Testing Strategy)

### (V4 升级) Backend Tests (Pytest)

#### (V4 核心) 租户隔离测试
必须编写集成测试，模拟两个不同的租户(租户 A, 租户 B)调用 `/api/v1/query`，并断言租户 A 绝不会看到租户 B 的数据。

**示例测试**:

```python
# tests/test_tenant_isolation.py
import pytest
from fastapi.testclient import TestClient

def test_tenant_isolation(client: TestClient):
    # 租户 A 的 JWT
    tenant_a_token = create_test_jwt(tenant_id="tenant-a")

    # 租户 B 的 JWT
    tenant_b_token = create_test_jwt(tenant_id="tenant-b")

    # 租户 A 查询
    response_a = client.post(
        "/api/v1/query",
        headers={"Authorization": f"Bearer {tenant_a_token}"},
        json={"question": "显示所有数据"}
    )

    # 租户 B 查询
    response_b = client.post(
        "/api/v1/query",
        headers={"Authorization": f"Bearer {tenant_b_token}"},
        json={"question": "显示所有数据"}
    )

    # 断言：租户 A 和 B 的数据完全不同
    assert response_a.json() != response_b.json()
    assert "tenant-a" in response_a.json()["answer"]
    assert "tenant-b" in response_b.json()["answer"]
```

#### (V4 核心) 数据源测试
必须测试 `/data-sources/database` 端点，验证无效的连接字符串会被拒绝(返回 400)。

```python
def test_invalid_connection_string(client: TestClient, auth_token: str):
    response = client.post(
        "/api/v1/data-sources/database",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "测试数据库",
            "connection_string": "invalid_connection_string"
        }
    )
    assert response.status_code == 400
```

### Frontend Tests (Jest + React Testing Library)

```typescript
// tests/api.test.ts
import { queryAPI } from '@/lib/api';

describe('API Client', () => {
  it('should include JWT token in request', async () => {
    const mockFetch = jest.fn();
    global.fetch = mockFetch;

    await queryAPI('test question');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': expect.stringContaining('Bearer ')
        })
      })
    );
  });
});
```

### 测试覆盖率要求
- **单元测试**: > 80% 代码覆盖率
- **集成测试**: 覆盖所有关键 API 端点
- **E2E 测试**: 覆盖主要用户流程

---

## 第 13 部分: 编码标准 (Coding Standards)

### (V4 升级) Critical Fullstack Rules (关键全栈规则)

#### 规则 1 (UI 规范)
绝不能使用自定义 CSS。必须使用 **"the curator."** 规范(`style.md`)。

#### 规则 2 (API 调用)
前端必须通过 `lib/api.ts` 服务层并使用 Auth JWT 调用 API。

#### 规则 3 (环境变量)
绝不能在代码中硬编码任何密钥(特别是 `ZHIPUAI_API_KEY`)。

#### 规则 4 (错误处理)
前端必须在 API 调用中使用 `finally { setIsLoading(false); }`。

#### 规则 5 (V4 核心)
**租户隔离！** 所有后端服务(`agent_core.py`, `sql_chain.py`, `rag_chain.py`)必须接受 `tenant_id` 作为参数，并将其用于所有数据检索。

### 代码质量标准

#### Python (Backend)
- 使用 **Black** 进行代码格式化
- 使用 **Pylint** 进行代码检查
- 使用 **mypy** 进行类型检查
- 遵循 PEP 8 规范

#### TypeScript (Frontend)
- 使用 **Prettier** 进行代码格式化
- 使用 **ESLint** 进行代码检查
- 启用严格的 TypeScript 模式
- 遵循 Airbnb 风格指南

### Git 工作流
- 使用功能分支开发
- 提交前必须通过所有测试
- 代码审查必须至少一人批准
- 使用语义化提交消息

---

## 第 14 部分: 错误处理策略 (Error Handling Strategy)

### 后端错误处理

#### HTTP 状态码规范
- `200`: 成功
- `201`: 创建成功
- `400`: 客户端错误(无效请求)
- `401`: 未认证
- `403`: 无权限
- `404`: 资源未找到
- `429`: 速率限制
- `500`: 服务器内部错误

#### 错误响应格式

```json
{
  "error": {
    "code": "TENANT_NOT_FOUND",
    "message": "租户数据源未找到",
    "details": {
      "tenant_id": "abc123"
    }
  }
}
```

#### 异常处理示例

```python
# backend/src/app/core/exceptions.py
class TenantNotFoundException(Exception):
    """租户未找到异常"""
    pass

class InvalidConnectionStringException(Exception):
    """无效的连接字符串异常"""
    pass

# 在 FastAPI 中注册异常处理器
@app.exception_handler(TenantNotFoundException)
async def tenant_not_found_handler(request: Request, exc: TenantNotFoundException):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "TENANT_NOT_FOUND",
                "message": str(exc)
            }
        }
    )
```

### 前端错误处理

```typescript
// lib/api.ts
export async function queryAPI(question: string) {
  try {
    const response = await fetch('/api/v1/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error.message);
    }

    return response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

---

## 第 15 部分: 监控与可观测性 (Monitoring and Observability)

### 监控策略

#### MVP 阶段 (本地)
- **Docker Compose 日志**: `docker compose logs -f`
- **浏览器 F12 工具**: 前端调试
- **FastAPI 自动文档**: `http://localhost:8004/docs`

#### 生产环境

**应用监控**:
- Prometheus + Grafana
- 监控指标: CPU、内存、请求延迟、错误率

**日志聚合**:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- 结构化日志(JSON 格式)

**错误追踪**:
- Sentry
- 实时错误通知
- 错误堆栈追踪

### 日志规范

```python
# 结构化日志示例
import logging
import json

logger = logging.getLogger(__name__)

def log_query(tenant_id: str, question: str, duration: float):
    logger.info(json.dumps({
        "event": "query_processed",
        "tenant_id": tenant_id,
        "question": question,
        "duration_ms": duration * 1000,
        "timestamp": datetime.utcnow().isoformat()
    }))
```

---

## 第 16 部分: 检查表结果报告 (Checklist Results Report)

### 架构完整性检查

- [x] 多租户架构设计完成
- [x] 认证和授权机制定义
- [x] 数据模型设计完成
- [x] API 规范定义完成
- [x] 前端架构设计完成
- [x] 后端架构设计完成
- [x] 部署策略定义完成
- [x] 安全策略定义完成
- [x] 测试策略定义完成
- [x] 监控策略定义完成

### PRD 对齐检查

- [x] FR1: 多租户认证 ✓
- [x] FR2: 数据源连接页面 ✓
- [x] FR3: PostgreSQL 连接字符串 ✓
- [x] FR4: 文档上传 ✓
- [x] FR5: 租户隔离 API ✓
- [x] FR6: Agentic RAG-SQL ✓
- [x] FR7: 来源追溯 ✓
- [x] FR8: XAI 推理路径 ✓

- [x] NFR1: Docker Compose 部署 ✓
- [x] NFR2: 云就绪架构 ✓
- [x] NFR3: PostgreSQL 数据库 ✓
- [x] NFR4: MinIO 对象存储 ✓
- [x] NFR5: Zhipu API 集成 ✓
- [x] NFR6: "the curator." UI 规范 ✓

---

## 第 17 部分: 后续步骤 (Next Steps)

### Product Owner (PO) Handoff (PO 交接提示)

架构师 Winston 已完成并批准了 V4 全栈架构 (`architecture-v4.md`)。该文档与 PRD V4 完全对齐。

**交接内容**:
1. ✅ `prd-v4.md` - 产品需求文档
2. ✅ `architecture-v4.md` - 本架构文档
3. ✅ `style.md` - UI 设计规范

### 开发路线图

#### Phase 1: 基础设施搭建 (Story 1.1 - 1.5)
- 项目结构初始化
- Docker Compose 环境搭建
- 后端基础设施配置
- 前端基础设施配置
- 环境变量和配置管理

#### Phase 2: 认证和租户管理 (Story 2.1 - 2.5)
- 托管认证服务集成
- 租户管理系统
- 数据源连接管理
- 文档上传和管理
- 数据源管理界面

#### Phase 3: AI 核心功能 (Story 3.1 - 3.5)
- 租户隔离的查询 API
- RAG-SQL 链(租户隔离版)
- RAG 链(租户隔离版)
- 智谱 AI 集成和推理
- XAI 和融合引擎

#### Phase 4: UI 集成和测试 (Story 4.1 - 4.4)
- 聊天界面集成
- XAI 推理路径展示
- 溯源信息显示
- V4 功能集成测试

### 关键里程碑

1. **Week 1-2**: 完成 Phase 1 (基础设施)
2. **Week 3-4**: 完成 Phase 2 (认证和租户)
3. **Week 5-6**: 完成 Phase 3 (AI 核心)
4. **Week 7-8**: 完成 Phase 4 (UI 和测试)

### 成功标准

- ✅ 本地 Docker Compose 一键启动
- ✅ 多租户完全隔离
- ✅ 所有测试通过
- ✅ 性能达标(< 8 秒响应)
- ✅ 准备好部署到云服务器

---

## 附录: 技术参考

### 相关文档
- [PRD V4](./prd-v4.md)
- [UI 设计规范](./style.md)
- [Story 文档](./stories/)

### 外部资源
- [Next.js 文档](https://nextjs.org/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Clerk 文档](https://clerk.com/docs)
- [Zhipu AI 文档](https://open.bigmodel.cn/dev/api)
- [Docker Compose 文档](https://docs.docker.com/compose/)

---

**文档版本**: V4.0 (合并版)
**创建日期**: 2025-11-16
**最后更新**: 2025-11-16
**架构师**: Winston (BMad)
**状态**: ✅ 已批准，准备开发

---

*本文档整合了 architecture.md、architecture-v4.md 和所有 architecture-shards 的内容，形成统一的 V4 架构文档。*

