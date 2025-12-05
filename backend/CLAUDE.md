[根目录](../CLAUDE.md) > **backend**

# Backend - FastAPI 后端服务模块

**模块类型**: 核心后端API服务
**技术栈**: Python 3.8+, FastAPI, SQLAlchemy 2.0, AsyncPG, Pydantic
**端口**: 8004 (Docker映射)
**最后更新**: 2025-12-05 11:43:00

---

## 模块职责

Backend模块是Data Agent V4的核心后端服务，负责：

- 🔐 **多租户认证**: JWT认证、租户隔离、权限管理
- 🚀 **RESTful API**: 标准化的API端点和数据验证
- 💾 **数据持久化**: PostgreSQL连接池、ORM模型、事务管理
- 📁 **对象存储**: MinIO集成、文件上传、文档管理
- 🔍 **向量检索**: ChromaDB集成、语义搜索、知识管理
- 🤖 **AI集成**: 智谱GLM API、对话式分析、推理路径
- 📊 **健康监控**: 服务健康检查、性能监控、日志记录

---

## 入口与启动

### 主入口文件
```python
# src/app/main.py - FastAPI应用入口
from src.app.main import app

# 应用配置
- 应用名称: "Data Agent Backend"
- 版本: "1.0.0"
- API前缀: "/api/v1"
- 文档地址: "/docs" (仅开发环境)
```

### 启动方式
```bash
# Docker方式 (推荐)
docker-compose up backend

# 本地开发
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8004
```

### 生命周期管理
- **启动时**: 配置验证 → 服务健康检查 → 数据库初始化
- **运行时**: 请求日志 → 性能监控 → 异常处理
- **关闭时**: 资源清理 → 连接关闭 → 事件记录

---

## 对外接口 (API Endpoints)

### API路由结构
```
/api/v1/
├── health/          # 健康检查 (无需认证)
├── auth/            # 认证相关
├── tenants/         # 租户管理
├── data-sources/    # 数据源连接
├── documents/       # 文档管理
├── llm/            # AI对话服务
├── config/         # 配置验证
├── security/       # 安全配置
└── test/           # 服务测试
```

### 核心API端点

#### 健康检查 (Health)
```python
GET /api/v1/health/status     # 详细健康检查
GET /api/v1/health/ping       # 简单ping
GET /api/v1/health/database   # 数据库健康状态
GET /api/v1/health/services   # 服务状态总览
```

#### 租户管理 (Tenants)
```python
GET    /api/v1/tenants/           # 获取租户列表
POST   /api/v1/tenants/           # 创建新租户
GET    /api/v1/tenants/{id}       # 获取租户详情
PUT    /api/v1/tenants/{id}       # 更新租户信息
DELETE /api/v1/tenants/{id}       # 删除租户
```

#### 数据源管理 (Data Sources)
```python
GET    /api/v1/data-sources/           # 获取数据源列表
POST   /api/v1/data-sources/           # 创建数据源连接
GET    /api/v1/data-sources/{id}       # 获取数据源详情
PUT    /api/v1/data-sources/{id}       # 更新数据源
DELETE /api/v1/data-sources/{id}       # 删除数据源
POST   /api/v1/data-sources/{id}/test  # 测试数据源连接
```

#### 文档管理 (Documents)
```python
GET    /api/v1/documents/           # 获取文档列表
POST   /api/v1/documents/           # 上传新文档
GET    /api/v1/documents/{id}       # 获取文档详情
DELETE /api/v1/documents/{id}       # 删除文档
GET    /api/v1/documents/{id}/download # 下载文档
```

#### AI对话服务 (LLM)
```python
POST   /api/v1/llm/chat            # 对话式AI分析
POST   /api/v1/llm/query           # 结构化数据查询
GET    /api/v1/llm/history         # 对话历史
DELETE /api/v1/llm/history         # 清除对话历史
```

### 认证与授权
- **JWT Token**: 基于Clerk的JWT认证
- **租户隔离**: 所有业务接口强制tenant_id过滤
- **API Key**: 可选的API密钥认证
- **权限控制**: 基于租户的资源访问控制

---

## 关键依赖与配置

### 核心依赖包
```python
# Web框架与ASGI服务器
fastapi==0.111.0
uvicorn[standard]==0.24.0

# 数据库与ORM
sqlalchemy==2.0.31
asyncpg==0.29.0
psycopg2-binary==2.9.9

# 认证与安全
python-jose[cryptography]==3.3.0
PyJWT==2.8.0
cryptography==41.0.7

# 存储与向量数据库
minio==7.2.0
chromadb==0.4.18

# AI服务
zhipuai==2.0.1
openai==1.51.0  # OpenRouter兼容性

# 监控与日志
structlog==24.4.0
```

### 环境变量配置
```bash
# 必需配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dataagent
ZHIPUAI_API_KEY=your_zhipu_api_key_here
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key

# 认证配置
CLERK_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...
CLERK_DOMAIN=clerk.accounts.dev

# 可选配置
OPENROUTER_API_KEY=your_openrouter_key
ENVIRONMENT=development
DEBUG=true
```

### 配置验证机制
- **启动验证**: 应用启动时自动验证所有配置
- **安全检查**: 检测弱密码和不安全配置
- **服务连通性**: 验证所有外部服务的连接状态
- **密钥强度**: 验证密钥长度和复杂度要求

---

## 数据模型

### 核心实体模型

#### Tenant (租户)
```python
class Tenant(Base):
    id: str (PK, Clerk user_id)
    email: str (UNIQUE)
    display_name: str
    clerk_user_id: str (UNIQUE)
    is_active: bool
    max_data_sources: int
    max_documents: int
    storage_quota_mb: int
```

#### DataSourceConnection (数据源连接)
```python
class DataSourceConnection(Base):
    id: int (PK)
    tenant_id: str (FK)
    name: str
    connection_type: str (postgresql, mysql, etc.)
    connection_string: str (encrypted)
    is_active: bool
    host: str
    port: int
    database_name: str
```

#### KnowledgeDocument (知识文档)
```python
class KnowledgeDocument(Base):
    id: int (PK)
    tenant_id: str (FK)
    title: str
    file_name: str
    file_path: str (MinIO object path)
    file_size: int
    processing_status: str (pending, processing, completed, failed)
    vectorized: bool
    vector_count: int
    chroma_collection: str
```

### 数据库策略
- **多租户隔离**: 基于tenant_id的行级安全
- **软删除**: 重要数据使用is_active标记软删除
- **审计日志**: created_at, updated_at时间戳
- **索引优化**: tenant_id + 业务字段的复合索引

---

## 服务层架构

### MinIO对象存储服务
```python
# src/app/services/minio_client.py
class MinIOService:
    - 文件上传/下载
    - 存储桶管理
    - 预签名URL生成
    - 文件元数据管理
```

### ChromaDB向量数据库服务
```python
# src/app/services/chromadb_client.py
class ChromaDBService:
    - 文档向量化
    - 语义搜索
    - 集合管理
    - 向量存储/检索
```

### 智谱AI服务
```python
# src/app/services/zhipu_client.py
class ZhipuService:
    - GLM模型调用
    - 对话管理
    - 重试机制
    - 响应解析
```

### LLM服务编排
```python
# src/app/services/llm_service.py
class LLMService:
    - RAG链实现
    - SQL生成
    - 结果解释
    - 推理路径记录
```

---

## 测试与质量

### 测试结构
```
tests/
├── conftest.py              # 测试配置和fixtures
├── api/v1/                  # API端点测试
│   ├── test_health.py
│   ├── test_tenants.py
│   └── test_llm_endpoints.py
├── services/                # 服务层测试
│   ├── test_minio_client.py
│   ├── test_zhipu_client.py
│   └── test_llm_service.py
└── data/                    # 数据模型测试
    └── test_models.py
```

### 测试工具
- **pytest**: 测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-cov**: 代码覆盖率
- **httpx**: HTTP客户端测试

### 代码质量工具
- **black**: 代码格式化
- **isort**: 导入排序
- **flake8**: 代码检查
- **mypy**: 类型检查

### 运行测试
```bash
# 所有测试
pytest tests/ -v --cov

# 特定测试
pytest tests/api/v1/test_health.py -v

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

---

## 安全与性能

### 安全措施
- **输入验证**: Pydantic模型验证所有输入
- **SQL注入防护**: SQLAlchemy ORM参数化查询
- **文件上传安全**: 文件类型和大小限制
- **密钥管理**: 环境变量 + 密钥轮换机制
- **CORS配置**: 跨域请求安全控制

### 性能优化
- **数据库连接池**: 异步连接池管理
- **查询优化**: 索引优化 + N+1查询防护
- **缓存策略**: Redis缓存热点数据
- **异步处理**: 全程async/await模式
- **请求限流**: API调用频率限制

### 监控与日志
- **结构化日志**: structlog JSON格式日志
- **性能监控**: 请求时间和数据库查询时间
- **错误追踪**: 完整的异常堆栈和上下文
- **健康检查**: 多层次的服务健康监控

---

## 常见问题 (FAQ)

### Q: 如何添加新的API端点？
A: 在`src/app/api/v1/endpoints/`下创建新模块，然后在`__init__.py`中注册路由。确保包含租户隔离和适当的错误处理。

### Q: 数据库模型变更怎么办？
A: 修改`src/app/data/models.py`后，使用Alembic创建迁移：
```bash
alembic revision --autogenerate -m "描述变更"
alembic upgrade head
```

### Q: 如何调试智谱AI集成问题？
A: 检查API密钥配置，查看日志中的请求/响应，使用`/api/v1/test/zhipu`端点进行连接测试。

### Q: MinIO文件上传失败怎么处理？
A: 检查存储桶权限、网络连接和访问密钥。使用健康检查端点验证MinIO连接状态。

---

## 相关文件清单

### 核心文件
- `src/app/main.py` - FastAPI应用入口
- `src/app/core/config.py` - 配置管理
- `src/app/data/models.py` - 数据模型
- `src/app/data/database.py` - 数据库连接
- `requirements.txt` - 依赖包列表

### API端点
- `src/app/api/v1/__init__.py` - 路由注册
- `src/app/api/v1/endpoints/` - 各模块端点实现

### 服务层
- `src/app/services/minio_client.py` - MinIO集成
- `src/app/services/chromadb_client.py` - ChromaDB集成
- `src/app/services/zhipu_client.py` - 智谱AI集成
- `src/app/services/llm_service.py` - LLM服务编排

### 测试文件
- `tests/conftest.py` - 测试配置
- `tests/api/v1/` - API测试
- `tests/services/` - 服务测试

### 配置文件
- `pytest.ini` - pytest配置
- `Dockerfile` - Docker构建配置

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更类型 | 描述 | 作者 |
|------|------|----------|------|------|
| 2025-11-17 | V4.1 | 🆕 新增 | 后端模块AI上下文文档创建 | AI Assistant |
| 2025-11-16 | V4.1 | 🔧 更新 | 增加智谱AI集成和LLM服务 | John |
| 2025-11-15 | V4.0 | 🔄 重构 | 重构为多租户SaaS架构 | John |
| 2025-11-14 | V3.0 | ⚙️ 优化 | 添加全面的安全配置验证 | John |

---

**🔧 开发提示**: 所有API操作都应包含适当的错误处理和租户隔离。使用`@tenant_required`装饰器确保数据安全。测试新功能时，优先验证多租户数据隔离。**