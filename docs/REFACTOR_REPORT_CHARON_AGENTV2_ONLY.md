# Charon 分支重构报告（AgentV2-only）

> 仓库：`1274866478-stack/insight-agent`  
> 分支：`charon`  
> 日期：2026-02-19

## 0. Step0/1 结论

- 运行编排入口：`docker-compose.yml`（`frontend=./apps/frontend`、`backend=./apps/backend`、`agent=./agent`）。
- Agent 挂载与导入前提：挂载到容器 `/agent`，并设置 `PYTHONPATH=/app:/`。
- 后端入口：`apps/backend/src/app/main.py`。
- 路由聚合：
  - v1：`apps/backend/src/app/api/v1/__init__.py`
  - v2：`apps/backend/src/app/api/v2/__init__.py`
- AgentV2 后端唯一调用边界：`apps/backend/src/app/integrations/agentv2_gateway/gateway.py`。
- 结论：后端业务代码已收敛为 `gateway -> agent/`，backend 业务层已移除对 `agent.*` 的直接 import（仅 gateway 保留）。

## 1. 重构后目录树（4 层）+ 职责

```text
apps/backend
|-- src/app
|   |-- api/
|   |   |-- v1/
|   |   `-- v2/
|   |-- core/
|   |-- data/
|   |-- domains/
|   |   |-- tenants/
|   |   |-- data_sources/
|   |   |-- documents/
|   |   |-- llm/
|   |   |-- rag_sql/
|   |   `-- semantic_layer/
|   |-- integrations/
|   |   |-- agentv2_gateway/
|   |   |-- storage_minio/
|   |   |-- vectordb_chroma/
|   |   |-- vectordb_qdrant/
|   |   |-- cube/
|   |   `-- llm_providers/
|   |-- middleware/
|   |-- schemas/
|   |-- services/
|   `-- shared/
`-- uploads/

apps/frontend
|-- src/app
|-- src/components
|-- src/services
`-- src/store

agent
|-- core/
|-- graphs/
|-- middleware/
|-- tools/
`-- subagents/

infrastructure
|-- database/migrations/versions/
`-- storage/data_storage/

tools
`-- deployment/

docs
`-- *.md
```

### backend 模块职责（一行版）

- `api/v1`：历史 API 兼容层与 HTTP 适配。
- `api/v2`：AgentV2 主查询 API（`/api/v2/query`）。
- `core`：配置、鉴权、日志、监控、安全等跨域基础能力。
- `shared`：跨域共享契约（当前含 AgentV2 gateway protocol）。
- `domains/*`：业务域 facade（先做薄层适配，复用既有 services）。
- `integrations/agentv2_gateway`：后端调用 AgentV2 的唯一边界层。
- `integrations/storage_minio`：MinIO 封装。
- `integrations/vectordb_chroma`：Chroma 封装。
- `integrations/vectordb_qdrant`：Qdrant 封装。
- `integrations/cube`：Cube 语义层封装。
- `integrations/llm_providers`：LLM Provider 封装。

## 2. 业务代码 vs 非业务代码清单（保留/删除/合并）

### 保留（业务）

- `apps/backend/src/app/services/*`：保留现有业务实现，避免流程重写。
- `apps/backend/src/app/api/v1/endpoints/query.py`：保留 v1 行为，对 Agent 调用改为 gateway。
- `apps/backend/src/app/api/v2/endpoints/query_v2.py`：保留 v2 行为，对 Agent 运行时改为 gateway。

### 新增（结构与兼容）

- `apps/backend/src/app/domains/*`：新增业务域 facade 骨架。
- `apps/backend/src/app/integrations/*`：新增外部系统封装层。
- `apps/backend/src/app/integrations/agentv2_gateway/*`：新增 AgentV2-only 网关。
- `apps/backend/src/app/shared/contracts.py`：新增跨层协议契约。

### 删除（高置信非业务/废弃）

- `agent/test_results.json`
- `apps/backend/test_stats_output.txt`
- `apps/backend/src/app/services/agent/DIAGNOSIS.md`
- `apps/backend/src/app/services/agent/agent_service.py`（旧 Agent 服务实现，已无引用）
- `apps/backend/src/app/api/v1/endpoints/performance.py`
- `apps/backend/src/app/api/v1/endpoints/performance_enhanced.py`
- `apps/backend/src/app/api/v1/endpoints/rag.py`
- `apps/backend/src/app/api/v1/endpoints/reasoning_fix.py`
- `apps/backend/src/app/api/v2/endpoints/query_stream_v2.py`
- `apps/backend/src/app/services/qdrant_client.py`
- `apps/frontend/src/components/chat/ChatTest.tsx`
- `apps/frontend/src/components/chat/FloatingActions.tsx`
- `apps/frontend/src/components/data-sources/DataSourceStatsPanel.tsx`
- `apps/frontend/src/components/tenant/__init__.tsx`
- `apps/frontend/src/components/ui/button-enhanced.tsx`
- `apps/frontend/src/components/xai/citation-styles.ts`

## 3. 变更摘要

### 结构迁移

- 新增 `domains/`、`integrations/`、`shared/` 三层骨架。
- API v1/v2 聚合层精简，只保留现役端点入口。

### AgentV2-only 治理

- 新增统一网关：`integrations/agentv2_gateway/gateway.py`。
- v1 查询链：`api/v1/query` -> `services/agent_service.run_agent_query` shim -> `agentv2_gateway.run_legacy_query`。
- v1 SOTA 链：`api/v1/query/sota` -> `agentv2_gateway.run_swarm_query`。
- v2 查询链：factory/cache/middleware/list_tables/context/validator 全部改走 gateway。
- 修复 v2 响应模型与运行时不一致：`processing_steps` 支持对象结构，补齐 `processing_time_ms`。

### shim 与 re-export

- `services/agent_service.py` 保留原签名，最小转发到 AgentV2 gateway。
- `domains/*/service.py` 与 `integrations/*` 使用 facade/re-export，降低导入改动面。

### 日志/调试清理

- 删除 v1 query 中的 `print(...)` 调试输出。
- 删除 v1 llm 端点中的 `print(...)` 调试输出，统一改为 logger。
- 清理 `reasoning_service`、`few_shot_rag/*`、`prompt_generator` 中的调试打印/测试块。
- 删除 v2 endpoint 的 `__main__` 测试启动代码。

## 4. 风险点与回滚策略

### 风险点

- import 路径风险：历史代码若绕过 shim 直接依赖旧 Agent 入口会失效。
- docker 挂载风险：`./agent:/agent` 与 `PYTHONPATH=/app:/` 是 gateway 正常导入前提。
- API 兼容风险：v2 `processing_steps` 模型已修复为兼容对象/字符串混合格式。
- 健康检查风险：外部 LLM key 未配置时 `/health` 可能是 `unhealthy`，但不代表进程启动失败。

### 回滚策略

- 回滚 gateway：仅回退 `integrations/agentv2_gateway/gateway.py`。
- 回滚 v2：仅回退 `api/v2/endpoints/query_v2.py`。
- 回滚路由聚合：分别回退 `api/v1/__init__.py` 与 `api/v2/__init__.py`。
- 回滚删除文件：通过 Git 恢复对应路径。

## 5. 低耦合规则落地

- API 层：只做 HTTP 适配，不直接 import `agent.*`。
- domains 层：当前通过 facade 复用 services，不跨 domain 直接互相 import。
- integrations 层：只封装外部系统，不承载业务编排。
- AgentV2 规则：backend 仅 `integrations/agentv2_gateway` 可直接 import `agent.*`，其余模块禁止直连。

## 6. 验证命令与结果

### 启动

```bash
docker compose up -d
```

- 结果：backend/frontend/postgres/minio/chroma/cube/qdrant 均启动成功。

### smoke

```bash
GET  /health
GET  /docs
GET  /api/v1/
GET  /api/v2/query/health
POST /api/v2/query/   {"query":"smoke test"}
POST /api/v1/query/sota   {"query":"sota smoke"}
```

- 结果：
  - `/docs` = 200
  - `/api/v1/` = running
  - `/api/v2/query/health` = healthy
  - `/api/v2/query/` = success=true
  - `/api/v1/query/sota` = 200
  - `/health` = unhealthy（`zhipu_ai` 未配置，属外部依赖状态）
