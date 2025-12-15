# Agent 集成完成指南

本文档说明如何解决 Agent 集成后的两个限制问题。

## 已解决的问题

### 1. ✅ MCP 服务器自动启动

**问题**：MCP 服务器（mcp-echarts）需要手动启动，导致图表功能不可用。

**解决方案**：已在 `docker-compose.yml` 中添加 MCP 服务器服务，实现自动启动。

**配置位置**：
- `docker-compose.yml` - 添加了 `mcp_echarts` 服务
- `Agent/Dockerfile.mcp` - MCP 服务器的 Dockerfile

**使用方法**：
```bash
# 启动所有服务（包括 MCP 服务器）
docker-compose up -d

# 或者单独启动 MCP 服务器
docker-compose up -d mcp_echarts
```

**验证**：
- MCP 服务器将在 `http://localhost:3033/sse` 上运行
- 后端 Agent 会自动连接到该服务

### 2. ✅ 前端集成 Agent 功能

**问题**：前端无法使用 Agent 功能，因为 API 客户端没有调用正确的端点。

**解决方案**：
1. 更新了前端 API 客户端，使其在提供 `connection_id` 时自动使用 `/query` 端点
2. 更新了 `chatStore`，确保正确传递数据源 ID
3. 修复了后端类型不匹配问题（`connection_id` 从 `int` 改为 `str`）

**修改的文件**：
- `frontend/src/lib/api-client.ts` - 添加了 `sendAgentQuery` 方法
- `frontend/src/store/chatStore.ts` - 传递 `connection_id` 参数
- `backend/src/app/schemas/query.py` - 修复类型定义
- `backend/src/app/services/data_source_service.py` - 修复类型定义

**使用方法**：
1. 在前端选择数据源
2. 发送查询时，系统会自动使用 Agent 处理（如果提供了数据源 ID）
3. 如果没有选择数据源，将使用标准的 LLM 聊天模式

## 工作流程

### 使用 Agent 查询（推荐）

1. **选择数据源**：在 AI Assistant 页面选择要查询的数据源
2. **发送查询**：输入自然语言查询，例如："查询最近10个订单"
3. **Agent 处理**：
   - 前端自动调用 `/api/v1/query` 端点
   - 传递 `connection_id` 参数
   - 后端使用 LangGraph SQL Agent 处理查询
   - 自动生成 SQL、执行查询、生成图表（如果适用）
4. **返回结果**：显示查询结果、SQL 语句和解释

### 使用标准 LLM 聊天

1. **不选择数据源**：在 AI Assistant 页面选择"所有数据源"或留空
2. **发送查询**：输入问题
3. **LLM 处理**：使用标准的 LLM Chat Completions API
4. **返回结果**：显示 LLM 生成的回答

## 验证步骤

### 1. 验证 MCP 服务器

```bash
# 检查 MCP 服务器是否运行
curl http://localhost:3033/sse

# 检查 Docker 容器状态
docker-compose ps mcp_echarts
```

### 2. 验证前端集成

1. 启动前端：`cd frontend && npm run dev`
2. 打开浏览器：`http://localhost:3000`
3. 导航到 AI Assistant 页面
4. 选择一个数据源
5. 发送查询："查询数据库中有哪些表？"
6. 应该看到 Agent 生成的 SQL 和结果

### 3. 验证后端集成

```bash
# 检查后端日志
docker-compose logs backend | grep -i agent

# 测试查询端点
curl -X POST http://localhost:8004/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "查询数据库中有哪些表？",
    "connection_id": "your-data-source-id"
  }'
```

## 故障排除

### MCP 服务器无法启动

1. 检查 Node.js 是否已安装：`node --version`
2. 检查 Docker 容器日志：`docker-compose logs mcp_echarts`
3. 手动测试 MCP 服务器：`mcp-echarts -t sse -p 3033`

### Agent 查询失败

1. 检查数据源 ID 是否正确传递
2. 检查后端日志：`docker-compose logs backend`
3. 验证数据源连接是否正常
4. 检查 Agent 依赖是否已安装

### 前端无法调用 Agent

1. 检查浏览器控制台是否有错误
2. 检查网络请求是否发送到 `/api/v1/query`
3. 验证 `connection_id` 是否正确传递
4. 检查 API 客户端代码是否正确更新

## 下一步

- [ ] 添加图表可视化支持
- [ ] 优化 Agent 响应格式
- [ ] 添加查询历史记录
- [ ] 实现查询缓存机制




