# Agent 集成已知限制详细说明

本文档详细说明 Agent 集成过程中的两个已知限制，包括具体影响、原因和解决方案。

---

## 限制 1: 前端集成限制

### 问题描述

**当前状态**：
- ✅ 后端 API `/api/v1/query` 已成功集成 Agent 功能
- ✅ 后端可以正确处理 Agent 查询并返回 `QueryResponseV3` 格式
- ❌ 前端目前**未使用** `/api/v1/query` 端点
- ❌ 前端使用 `/llm/chat/completions` 端点，该端点不支持 Agent 的 SQL 查询功能

### 具体表现

#### 1. 前端 API 调用方式

**当前实现** (`frontend/src/lib/api-client.ts:235-282`):
```typescript
async sendQuery(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
  // 构建消息列表
  const messages: ChatMessage[] = []
  
  // 转换为LLM Chat Completions格式
  const chatRequest: ChatCompletionRequest = {
    messages,
    temperature: 0.7,
    stream: false,
    enable_thinking: false,
    data_source_ids: request.context?.data_sources,
    use_agent: false,  // ❌ 禁用 LangGraph Agent 模式
  }

  // ❌ 调用 /llm/chat/completions 而不是 /api/v1/query
  const response = await this.request<BackendChatCompletionResponse>('/llm/chat/completions', {
    method: 'POST',
    body: JSON.stringify(chatRequest),
  })
}
```

**期望实现**:
```typescript
async sendQuery(request: ChatQueryRequest): Promise<ApiResponse<QueryResponseV3>> {
  // ✅ 应该调用 /api/v1/query
  const response = await this.request<QueryResponseV3>('/query', {
    method: 'POST',
    body: JSON.stringify({
      query: request.query,
      connection_id: request.context?.data_sources?.[0],  // 数据源ID
      enable_cache: true,
      force_refresh: false
    }),
  })
}
```

#### 2. 响应格式不匹配

**后端返回** (`QueryResponseV3`):
```typescript
{
  query_id: string
  generated_sql: string          // ✅ Agent 生成的 SQL
  results: Array<Record<string, any>>  // ✅ 查询结果数据
  execution_result: {
    success: boolean
    data: object
    chart: {                      // ✅ 图表数据（Base64）
      chart_type: string
      chart_data: string          // Base64 编码的图片
    }
  }
  explanation: string            // ✅ Agent 的解释
  // ... 其他字段
}
```

**前端期望** (`ChatQueryResponse`):
```typescript
{
  answer: string                  // ✅ 只有文本回答
  sources?: string[]              // ✅ 数据源
  reasoning?: string              // ✅ 推理过程
  confidence?: number            // ✅ 置信度
  // ❌ 缺少：generated_sql, results, chart_data
}
```

#### 3. 功能缺失

前端当前**无法**：
- ❌ 显示 Agent 生成的 SQL 查询
- ❌ 显示 SQL 查询结果表格
- ❌ 显示图表可视化（即使后端已返回 Base64 编码的图表数据）
- ❌ 使用 `connection_id` 参数选择特定数据源

### 影响范围

1. **用户体验**：
   - 用户无法看到 Agent 生成的 SQL
   - 用户无法看到结构化的查询结果表格
   - 用户无法看到数据可视化图表

2. **功能完整性**：
   - Agent 的 SQL 查询功能无法在前端使用
   - 图表生成功能无法在前端展示
   - 数据源选择功能无法使用

3. **开发工作**：
   - 需要更新前端 API 客户端
   - 需要更新前端类型定义
   - 需要添加 SQL 结果显示组件
   - 需要添加图表显示组件

### 解决方案

#### 步骤 1: 更新 API 客户端

**文件**: `frontend/src/lib/api-client.ts`

需要添加新的方法：
```typescript
// 新增：Agent 查询方法
async sendAgentQuery(request: {
  query: string
  connection_id?: string
  enable_cache?: boolean
  force_refresh?: boolean
}): Promise<ApiResponse<QueryResponseV3>> {
  return this.request<QueryResponseV3>('/query', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
```

#### 步骤 2: 更新类型定义

**文件**: `frontend/src/lib/api-client.ts`

需要添加 `QueryResponseV3` 类型：
```typescript
export interface QueryResponseV3 {
  query_id: string
  tenant_id: string
  original_query: string
  generated_sql: string
  results: Array<Record<string, any>>
  row_count: number
  processing_time_ms: number
  confidence_score: number
  explanation: string
  processing_steps: string[]
  validation_result?: {
    success: boolean
    error?: string
  }
  execution_result?: {
    success: boolean
    data?: any
    chart?: {
      chart_type: string
      chart_data?: string  // Base64 编码的图片
      title?: string
      // ... 其他图表配置
    }
  }
  correction_attempts: number
  timestamp: string
}
```

#### 步骤 3: 更新 ChatStore

**文件**: `frontend/src/store/chatStore.ts`

需要修改 `_sendOnlineMessage` 方法，支持两种模式：
- 模式 1: 使用 `/llm/chat/completions`（当前，用于普通对话）
- 模式 2: 使用 `/api/v1/query`（新增，用于 SQL Agent 查询）

#### 步骤 4: 添加 UI 组件

需要创建以下组件：
1. **SQL 显示组件**: 显示生成的 SQL 查询
2. **结果表格组件**: 显示查询结果数据
3. **图表显示组件**: 显示 Base64 编码的图表

### 优先级

- **高优先级**: 更新 API 客户端和类型定义
- **中优先级**: 更新 ChatStore 支持 Agent 查询
- **低优先级**: 添加 UI 组件（可以逐步实现）

---

## 限制 2: MCP 服务器启动限制

### 问题描述

**当前状态**：
- ✅ Agent 代码已集成，支持 MCP 协议
- ✅ 后端 API 已集成 Agent 功能
- ❌ MCP 服务器需要**单独启动**，不会自动启动
- ❌ 如果 MCP 服务器未运行，Agent 功能无法正常工作

### 具体表现

#### 1. MCP 服务器类型

Agent 需要两个 MCP 服务器：

**PostgreSQL MCP Server**:
- **传输方式**: stdio（标准输入输出）
- **启动方式**: 通过 `npx` 运行 `@modelcontextprotocol/server-postgres`
- **配置**: 在 `Agent/sql_agent.py` 中通过 `_get_mcp_config()` 配置
- **功能**: 提供数据库查询工具（`list_tables`, `get_schema`, `query` 等）

**ECharts MCP Server**:
- **传输方式**: SSE (Server-Sent Events)
- **启动方式**: 需要单独运行在 `localhost:3033`
- **配置**: 在 `Agent/sql_agent.py` 中配置 SSE URL
- **功能**: 提供图表生成工具（`get-chart` 等）

#### 2. 错误表现

当 MCP 服务器未运行时，会出现以下错误：

**PostgreSQL MCP Server 未运行**:
```
Error: Failed to start MCP server
No module named '@modelcontextprotocol/server-postgres'
```

**ECharts MCP Server 未运行**:
```
httpx.HTTPStatusError: Server error '502 Bad Gateway' 
for url 'http://localhost:3033/sse'
```

#### 3. 当前启动方式

**独立运行 Agent**:
```bash
# 需要手动启动 MCP 服务器（如果使用 ECharts）
# PostgreSQL MCP 通过 npx 自动启动
python Agent/run.py
```

**通过后端 API**:
```bash
# 后端启动时，MCP 服务器不会自动启动
# 需要单独启动 ECharts MCP 服务器
uvicorn src.app.main:app --reload
```

### 影响范围

1. **开发环境**：
   - 开发者需要手动启动 MCP 服务器
   - 增加了开发复杂度
   - 容易忘记启动导致功能不可用

2. **生产环境**：
   - 需要在部署脚本中启动 MCP 服务器
   - 需要管理 MCP 服务器的生命周期
   - 需要监控 MCP 服务器状态

3. **用户体验**：
   - 如果 MCP 服务器未运行，Agent 功能完全不可用
   - 错误消息可能不够清晰

### 解决方案

#### 方案 1: Docker Compose 集成（推荐）

**文件**: `docker-compose.yml`

添加 MCP 服务器服务：
```yaml
services:
  # ... 其他服务
  
  mcp-postgres:
    image: node:18
    command: npx -y @modelcontextprotocol/server-postgres
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
  
  mcp-echarts:
    image: node:18
    command: npx -y @modelcontextprotocol/server-echarts
    ports:
      - "3033:3033"
    environment:
      - PORT=3033
```

#### 方案 2: 启动脚本

**文件**: `scripts/start-mcp-servers.sh` 和 `scripts/start-mcp-servers.bat`

创建统一的启动脚本：
```bash
#!/bin/bash
# 启动 PostgreSQL MCP Server（通过 npx，自动启动）
# 启动 ECharts MCP Server
npx -y @modelcontextprotocol/server-echarts &
echo "MCP servers started"
```

#### 方案 3: 后端自动启动（复杂）

在 FastAPI 启动时自动启动 MCP 服务器：
```python
# backend/src/app/main.py
@app.on_event("startup")
async def startup_event():
    # 启动 MCP 服务器
    await start_mcp_servers()
```

### 当前状态

- ✅ **PostgreSQL MCP**: 通过 `npx` 自动启动（在 Agent 代码中）
- ❌ **ECharts MCP**: 需要手动启动或通过 Docker Compose

### 优先级

- **高优先级**: Docker Compose 集成（生产环境）
- **中优先级**: 启动脚本（开发环境）
- **低优先级**: 后端自动启动（可选）

---

## 总结

### 限制 1: 前端集成限制

| 项目 | 状态 |
|------|------|
| 后端 API 集成 | ✅ 已完成 |
| 前端 API 调用 | ❌ 需要更新 |
| 前端类型定义 | ❌ 需要更新 |
| 前端 UI 组件 | ❌ 需要创建 |
| **影响** | 用户无法使用 Agent 的 SQL 查询和图表功能 |

### 限制 2: MCP 服务器启动限制

| 项目 | 状态 |
|------|------|
| PostgreSQL MCP | ✅ 自动启动（通过 npx） |
| ECharts MCP | ❌ 需要手动启动 |
| Docker Compose 集成 | ❌ 需要添加 |
| **影响** | 开发和生产环境需要额外配置 |

### 建议的后续工作

1. **立即处理**（高优先级）:
   - 更新前端 API 客户端支持 `/api/v1/query`
   - 更新前端类型定义匹配 `QueryResponseV3`
   - 在 Docker Compose 中添加 MCP 服务器

2. **短期处理**（中优先级）:
   - 更新 ChatStore 支持 Agent 查询模式
   - 创建启动脚本管理 MCP 服务器
   - 添加 SQL 结果显示组件

3. **长期处理**（低优先级）:
   - 添加图表显示组件
   - 实现后端自动启动 MCP 服务器
   - 添加 MCP 服务器健康检查

---

## 相关文件

- 前端集成报告: `frontend_integration_report.json`
- 后端 API 端点: `backend/src/app/api/v1/endpoints/query.py`
- Agent 服务: `backend/src/app/services/agent_service.py`
- 前端 API 客户端: `frontend/src/lib/api-client.ts`
- 前端 ChatStore: `frontend/src/store/chatStore.ts`
- MCP 配置: `Agent/sql_agent.py` (函数 `_get_mcp_config`)

