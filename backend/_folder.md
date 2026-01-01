# Backend Module - FastAPI后端服务

## [MODULE]
**模块名称**: FastAPI后端服务模块
**职责**: 提供RESTful API、业务逻辑处理、数据持久化和外部服务集成 - 多租户SaaS架构的API网关和业务核心
**类型**: 后端服务模块

## [BOUNDARY]
**输入**:
- 前端HTTP请求（API调用）
- 外部服务响应（MinIO、ChromaDB、智谱AI）
- 数据库查询（PostgreSQL）

**输出**:
- JSON响应数据
- 文件流（文档下载）
- 健康检查状态
- 错误信息

## [PROTOCOL]
1. **async/await模式**: 所有API端点和服务必须使用异步模式
2. **租户隔离**: 所有业务API必须包含tenant_id过滤
3. **Pydantic验证**: 使用Pydantic模型验证所有请求和响应
4. **JWT认证**: 基于Clerk的JWT认证机制
5. **错误处理**: 统一的异常处理和用户友好的错误信息
6. **日志记录**: 结构化日志（JSON格式）记录所有请求和错误

## [STRUCTURE]
```
backend/
├── src/                     # 源代码目录
│   ├── app/                # 应用代码
│   │   ├── main.py         # FastAPI应用入口
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py   # 配置管理
│   │   │   ├── auth.py     # JWT认证
│   │   │   ├── logging.py  # 日志配置
│   │   │   └── security_monitor.py # 安全监控
│   │   ├── data/           # 数据层
│   │   │   ├── database.py # 数据库连接
│   │   │   └── models.py   # ORM模型
│   │   ├── api/            # API路由
│   │   │   └── v1/         # API v1版本
│   │   │       ├── endpoints/ # 端点实现
│   │   │       │   ├── health.py
│   │   │       │   ├── tenants.py
│   │   │       │   ├── data_sources.py
│   │   │       │   ├── documents.py
│   │   │       │   ├── llm.py
│   │   │       │   └── ...
│   │   │       └── __init__.py
│   │   ├── services/       # 业务服务
│   │   │   ├── llm_service.py
│   │   │   ├── minio_client.py
│   │   │   ├── chromadb_client.py
│   │   │   ├── zhipu_client.py
│   │   │   └── ...
│   │   ├── schemas/        # Pydantic模型
│   │   ├── middleware/     # 中间件
│   │   │   └── tenant_context.py
│   │   └── __init__.py
│   └── tests/              # 测试代码
├── data/                   # 测试数据
├── logs/                   # 日志输出
├── migrations/             # 数据库迁移
├── scripts/                # 后端脚本
├── requirements.txt        # Python依赖
├── Dockerfile             # Docker镜像
└── pytest.ini             # 测试配置
```

## [LINK]
**上游依赖**:
- [../frontend/](../frontend/_folder.md) - Next.js前端应用（发送HTTP请求）
- [../Agent/](../Agent/_folder.md) - LangGraph SQL智能代理（可选集成）
- 外部服务:
  - MinIO - 对象存储服务
  - ChromaDB - 向量数据库
  - 智谱AI - LLM服务
  - Clerk - JWT认证服务

**下游依赖**:
- [./src/app/core/](./src/app/core/_folder.md) - 核心配置（认证、日志、安全）
- [./src/app/data/](./src/app/data/_folder.md) - 数据层（数据库、ORM）
- [./src/app/api/v1/endpoints/](./src/app/api/v1/endpoints/_folder.md) - API端点（业务接口）
- [./src/app/services/](./src/app/services/_folder.md) - 业务服务（LLM、存储、向量）
- [./src/app/schemas/](./src/app/schemas/_folder.md) - 数据模型（Pydantic）
- [./src/app/middleware/](./src/app/middleware/_folder.md) - 中间件（租户隔离）

**调用方**:
- [../frontend/](../frontend/_folder.md) - 前端应用（API调用）
- 外部客户端（Postman、curl等）
- 测试套件（pytest）

## [STATE]
- FastAPI应用实例
- 数据库连接池
- MinIO/ChromaDB/智谱AI客户端
- 租户上下文（ContextVar）
- 服务健康状态

## [THREAD-SAFE]
是 - 使用asyncio和ContextVar确保并发安全

## [SIDE-EFFECTS]
- 数据库查询和修改
- 对象存储文件操作
- LLM API调用（消耗配额）
- 日志记录和监控数据上报
- 租户数据隔离
