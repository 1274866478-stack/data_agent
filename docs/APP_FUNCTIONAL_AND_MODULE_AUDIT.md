# Insight Agent 应用功能与模块实现说明

> 文档目标：说明当前应用“要做什么、怎么做、模块怎么拆、每个模块承担什么职责”。

## 1. 应用需要实现的核心功能

1. 多租户数据管理
- 租户、数据源、文档的增删改查与隔离。
- 通过 JWT/租户上下文保证请求级隔离。

2. 自然语言数据查询
- 用户提交自然语言问题，系统自动生成并执行查询，返回文本解释与结构化结果。
- 支持查询历史、状态、缓存管理。

3. AI 对话与流式响应
- 提供 `/api/v1/llm/*` 对话接口和流式事件输出。
- 支持 SQL 代码块检测后执行并回填结果。

4. AgentV2 驱动的查询编排
- `/api/v2/query` 通过 AgentV2 执行查询推理。
- 支持缓存、工具调用、租户级隔离。

5. 存储与向量能力
- MinIO 文件存储。
- Chroma/Qdrant 向量检索能力（按配置启用）。

6. 语义层与 SOTA 预留
- Cube.js 语义层能力预留。
- v1 的 SOTA 路由通过兼容层转发到 AgentV2 Swarm。

## 2. 当前实现方式（高层）

- 前端：Next.js，调用后端 v1/v2 API。
- 后端：FastAPI，统一入口 `src/app/main.py`。
- Agent 子系统：根目录 `agent/`，由后端通过网关访问。
- 运行编排：`docker-compose.yml` 启动 frontend/backend/postgres/minio/chroma/cube/qdrant。

## 3. 后端模块划分（重构后）

### 3.1 API 层（HTTP 适配）
- `apps/backend/src/app/api/v1/`
  - 职责：v1 路由聚合、请求参数校验、响应封装。
- `apps/backend/src/app/api/v2/`
  - 职责：v2 查询入口（AgentV2 主路由）。

### 3.2 Core 层（跨域基础设施）
- `apps/backend/src/app/core/`
  - 职责：配置、鉴权、日志、监控、异常策略。

### 3.3 Shared 层（共享契约）
- `apps/backend/src/app/shared/`
  - 职责：少量跨域契约（如 Agent gateway protocol）。

### 3.4 Domains 层（业务域）
- `apps/backend/src/app/domains/tenants/`
  - 功能：租户业务能力 facade。
  - 实现：复用 `services/tenant_service.py`。

- `apps/backend/src/app/domains/data_sources/`
  - 功能：数据源管理、连接信息。
  - 实现：复用 `services/data_source_service.py`。

- `apps/backend/src/app/domains/documents/`
  - 功能：文档管理与处理。
  - 实现：复用 `services/document_service.py`。

- `apps/backend/src/app/domains/llm/`
  - 功能：LLM 对话服务。
  - 实现：复用 `services/llm_service.py`。

- `apps/backend/src/app/domains/rag_sql/`
  - 功能：查询上下文编排。
  - 实现：封装 `services/query_context.py`。

- `apps/backend/src/app/domains/semantic_layer/`
  - 功能：语义层查询能力。
  - 实现：复用 `services/semantic_layer/cube_service.py`。

### 3.5 Integrations 层（外部系统封装）
- `apps/backend/src/app/integrations/storage_minio/`
  - 封装 MinIO 客户端。

- `apps/backend/src/app/integrations/vectordb_chroma/`
  - 封装 Chroma 客户端。

- `apps/backend/src/app/integrations/vectordb_qdrant/`
  - 封装 Qdrant REST 客户端。

- `apps/backend/src/app/integrations/cube/`
  - 封装 Cube 服务调用。

- `apps/backend/src/app/integrations/llm_providers/`
  - 封装 LLM provider 客户端入口。

- `apps/backend/src/app/integrations/agentv2_gateway/`
  - **唯一允许直接 import `agent/*` 的后端边界层**。
  - 负责：AgentFactory 获取、invoke、缓存访问、table 预取、上下文设置、swarm 转发、结果抽取与兼容适配。

## 4. AgentV2-only 调用链（已落地）

### v1 查询链
`/api/v1/query` → `services/agent_service.run_agent_query`（shim）
→ `integrations/agentv2_gateway.run_legacy_query`
→ `agent.core.AgentFactory(...).get_or_create_agent(...).invoke(...)`

### v1 SOTA 链
`/api/v1/query/sota` → `integrations/agentv2_gateway.run_swarm_query`
→ `agent.graphs.swarm_graph.run_swarm_query`

### v2 查询链
`/api/v2/query` → `integrations/agentv2_gateway`（factory/cache/tools/context）
→ `agent` 子系统

## 5. 关键接口与行为

- 健康检查：`/health`
- v1 基础：`/api/v1/*`
- v2 查询：`/api/v2/query/*`
- 文档与数据源相关仍保持原路由语义，未改请求/响应结构。

## 6. 兼容策略（Shim）

1. 保留 v1 的 `services/agent_service.py` 入口签名。
2. 将其核心调用重定向到 AgentV2 gateway，不再直接依赖旧 `sql_agent` 导入链。
3. v1 原有响应转换函数继续复用，减少对外行为变化风险。

## 7. 已清理的非业务内容（高置信）

- 删除运行产物与调试文档：
  - `apps/backend/test_stats_output.txt`
  - `agent/test_results.json`
  - `apps/backend/src/app/services/agent/DIAGNOSIS.md`
- 删除旧版后端 Agent 实现（无业务引用）：
  - `apps/backend/src/app/services/agent/agent_service.py`
- 删除 v2 endpoint 内 `__main__` 测试启动代码。
- 删除 v1 查询端点内直接 `print(...)` 调试输出。

## 8. 现阶段边界规则

- API 层只做请求/响应与参数适配。
- Domain 层通过 facade 暴露业务能力。
- Integration 层不承载业务编排。
- 后端内所有 Agent 直接依赖已收敛到 `integrations/agentv2_gateway`。

## 9. 后续建议

1. 继续将 v1/v2 中的大函数拆分到 domain service。
2. 给 gateway 增加统一异常码与可观测字段（request_id、tenant_id、session_id）。
3. 为 v1/v2 增加最小回归测试（健康、查询、缓存、错误路径）。
