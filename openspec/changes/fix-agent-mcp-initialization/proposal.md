# Change: 修复 Agent MCP 客户端初始化失败问题

## Why

Agent 服务在初始化 MCP 客户端时失败，错误信息显示 `FileNotFoundError: [Errno 2] No such file or directory`。这是因为：

1. **Docker 容器缺少 Node.js/npm**：MCP PostgreSQL 服务器需要通过 `npx` 命令启动 `@modelcontextprotocol/server-postgres`，但后端容器中没有安装 Node.js
2. **初始化失败导致 Agent 无法使用**：MCP 客户端初始化失败后，Agent 查询失败，系统回退到标准查询处理，无法执行 SQL 查询和图表生成
3. **错误处理不完善**：虽然代码中有错误处理，但缺少 Node.js 的情况没有被明确检测和报告，导致用户看到"幽灵数据"（从 System Prompt 返回的示例数据）

从后端日志分析可以看到：
- 错误发生在 `/Agent/sql_agent.py` 的 `_get_or_create_agent()` 函数中
- 尝试启动 PostgreSQL MCP 服务器进程时失败
- Agent 查询失败后，系统回退到标准查询处理，可能返回缓存或示例数据

## What Changes

### 方案一：在 Docker 镜像中安装 Node.js（推荐）
1. **更新后端 Dockerfile**：安装 Node.js 和 npm
   - 在 Dockerfile 中添加 Node.js 安装步骤
   - 确保 `npx` 命令可用

2. **验证安装**：在容器启动时验证 Node.js/npm 可用性

### 方案二：通过环境变量禁用 MCP（临时方案）
1. **改进错误处理**：当检测到 `npx` 不可用时，提供清晰的错误信息
2. **支持禁用 MCP**：通过环境变量 `DISABLE_MCP_TOOLS=true` 禁用 MCP，使用自定义工具（已有部分实现）
3. **文档说明**：明确说明如何配置和禁用 MCP

### 方案三：混合方案（推荐）
1. **安装 Node.js**：在 Dockerfile 中安装 Node.js
2. **改进错误处理**：添加更好的错误检测和报告
3. **优雅降级**：如果 MCP 初始化失败，使用自定义工具作为备选方案

## Impact

- **受影响的规范**: 无（这是问题修复，不涉及功能变更）
- **受影响的代码**:
  - `backend/Dockerfile`（添加 Node.js 安装）
  - `backend/src/app/services/agent/agent_service.py`（改进错误处理）
  - `Agent/sql_agent.py`（改进错误处理）
  - `docker-compose.yml`（如果需要更新配置）
- **新增依赖**: 
  - Node.js（用于运行 MCP PostgreSQL 服务器）
  - npm（包含在 Node.js 中）
- **环境要求**: 
  - Docker 镜像需要包含 Node.js（方案一和三）
  - 或者配置 `DISABLE_MCP_TOOLS=true` 使用自定义工具（方案二）

