# Change: 诊断并修复 Agent 执行失败问题

## Why

当前 `/api/v1/query` 端点虽然集成了 Agent 功能，但在实际查询时 Agent 调用失败，系统回退到标准查询处理。这导致：

1. **用户无法看到 SQL 查询结果**：`generated_sql` 为空，`results` 为空
2. **用户无法看到图表可视化**：`execution_result` 为 null，没有图表数据
3. **只显示推理过程**：用户只能看到 LLM 生成的文本解释，而不是实际的数据分析结果

从用户提供的 JSON 响应可以看出：
- `generated_sql`: ""（空）
- `results`: []（空数组）
- `execution_result`: null
- `explanation`: 包含"由于我无法直接执行SQL查询或生成图表"的文本

这表明 Agent 调用失败，系统回退到了标准查询处理流程（`QueryService.process_query`），该流程只调用 LLM 生成文本答案，不执行 SQL 查询。

## What Changes

### 诊断阶段
1. **添加详细日志**：在 `/api/v1/query` 端点中添加日志，记录：
   - `is_agent_available()` 的返回值
   - `data_source_id` 的值
   - Agent 调用的开始和结束
   - Agent 返回的 `success` 状态
   - Agent 调用失败时的具体错误信息

2. **检查 Agent 模块状态**：验证 Agent 模块是否正确导入，依赖是否满足

3. **检查 MCP 服务器状态**：验证 MCP Postgres 和 MCP ECharts 服务器是否正常运行

4. **检查数据库连接**：验证 Agent 能否正确连接到用户选择的数据源

### 修复阶段
根据诊断结果，修复以下可能的问题：

1. **Agent 模块导入问题**：
   - 确保 Agent 目录正确挂载到 Docker 容器
   - 确保 Python 路径配置正确
   - 确保所有依赖已安装

2. **MCP 服务器连接问题**：
   - 确保 MCP Postgres 服务器可以通过 `npx` 启动
   - 确保 MCP ECharts 服务器在 `localhost:3033` 运行（或配置正确的 URL）
   - 在 Docker Compose 中添加 MCP 服务器服务（如果尚未添加）

3. **数据库连接问题**：
   - 验证 `database_url` 格式正确
   - 验证 Agent 能使用提供的 `database_url` 连接数据库
   - 确保数据库连接字符串包含正确的认证信息

4. **Agent 调用错误处理**：
   - 改进错误处理，提供更详细的错误信息
   - 确保异常被正确捕获和记录
   - 避免静默失败

5. **配置问题**：
   - 验证 DeepSeek API 密钥配置正确
   - 验证 Agent 配置（`Agent/config.py`）正确读取后端配置

## Impact

- **受影响的规范**: 无（这是问题诊断和修复，不涉及功能变更）
- **受影响的代码**:
  - `backend/src/app/api/v1/endpoints/query.py`（添加详细日志）
  - `backend/src/app/services/agent_service.py`（改进错误处理和日志）
  - `Agent/sql_agent.py`（如果需要修复 MCP 配置或错误处理）
  - `docker-compose.yml`（如果需要添加 MCP 服务器服务）
  - `Agent/config.py`（如果需要修复配置读取）
- **新增依赖**: 无
- **环境要求**: 
  - Node.js（用于运行 MCP 服务器）
  - 确保 MCP ECharts 服务器运行在 `localhost:3033`（或配置正确的 URL）


