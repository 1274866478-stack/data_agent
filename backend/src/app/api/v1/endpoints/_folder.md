# API Endpoints

RESTful API 端点实现，V1 版本。

## Scope
定义所有 API 路由和处理函数，处理 HTTP 请求/响应。

## Members
| File | Description |
|------|-------------|
| `auth.py` | 认证相关端点 (JWT验证, Clerk集成) |
| `config.py` | 配置验证端点 |
| `data_sources.py` | 数据源管理 CRUD |
| `documents.py` | 文档上传和管理 |
| `file_upload.py` | 通用文件上传处理 |
| `health.py` | 健康检查 (数据库, MinIO, ChromaDB, AI) |
| `llm.py` | LLM 对话和分析服务 |
| `performance.py` | 性能监控端点 |
| `query.py` | SQL 查询执行 |
| `rag.py` | RAG 检索增强生成 |
| `reasoning.py` | 推理链服务 |
| `security.py` | 安全配置检查 |
| `tenants.py` | 租户管理 |
| `test.py` | 服务测试端点 |
| `upload.py` | 文件上传处理 |

## Constraints
- 所有业务端点必须包含租户隔离 (`tenant_id`)
- 使用 Pydantic 进行请求验证
- 统一错误处理格式
- 遵循 RESTful 约定
