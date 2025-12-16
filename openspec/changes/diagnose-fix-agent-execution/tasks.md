# 诊断并修复 Agent 执行失败问题 - 实施任务清单

## 1. 诊断阶段

### 1.1 添加详细日志到 `/api/v1/query` 端点
- [ ] 在 `backend/src/app/api/v1/endpoints/query.py` 的 `create_query` 函数中添加日志：
  - [ ] 记录 `is_agent_available()` 的返回值
  - [ ] 记录 `data_source_id` 的值
  - [ ] 记录 `use_agent` 的最终值
  - [ ] 在 Agent 调用前记录"开始调用 Agent"
  - [ ] 在 Agent 调用后记录 `agent_response.success` 的值
  - [ ] 如果 Agent 调用失败，记录完整的异常信息（包括堆栈跟踪）

### 1.2 添加详细日志到 Agent 服务
- [ ] 在 `backend/src/app/services/agent_service.py` 的 `run_agent_query` 函数中添加日志：
  - [ ] 记录函数调用开始（包含 question, thread_id, database_url）
  - [ ] 记录 `_agent_available` 的值
  - [ ] 记录配置更新（如果提供了 database_url）
  - [ ] 记录 `run_agent` 调用的开始和结束
  - [ ] 记录返回的 `response` 对象的关键字段（success, error, sql, data）
  - [ ] 记录所有异常（包括堆栈跟踪）

### 1.3 检查 Agent 模块状态
- [ ] 在 Docker 容器中运行诊断命令：
  ```bash
  docker exec dataagent-backend python -c "from src.app.services.agent_service import is_agent_available, _agent_available; print(f'Agent available: {is_agent_available()}'); print(f'_agent_available: {_agent_available}')"
  ```
- [ ] 验证 Agent 模块可以导入：
  ```bash
  docker exec dataagent-backend python -c "import sys; sys.path.insert(0, '/Agent'); from sql_agent import run_agent; print('Agent module imported successfully')"
  ```

### 1.4 检查 MCP 服务器状态
- [ ] 检查 MCP ECharts 服务器是否运行：
  ```bash
  curl http://localhost:3033/sse
  ```
- [ ] 检查 Docker Compose 中是否有 MCP 服务器服务
- [ ] 验证 MCP Postgres 服务器可以通过 `npx` 启动（在容器内测试）

### 1.5 检查数据库连接
- [ ] 验证 `database_url` 格式正确（从后端日志中提取）
- [ ] 在容器内测试数据库连接：
  ```bash
  docker exec dataagent-backend python -c "from src.app.services.data_source_service import DataSourceService; import asyncio; async def test(): service = DataSourceService(); url = await service.get_decrypted_connection_string('data_source_id', 'tenant_id', db); print(f'Database URL: {url}'); asyncio.run(test())"
  ```

### 1.6 执行一次测试查询并收集日志
- [ ] 在前端发送一次查询（选择单个数据源）
- [ ] 立即收集后端日志：
  ```bash
  docker logs --tail=500 dataagent-backend | grep -E "(Agent|agent|MCP|mcp|query|Query)"
  ```
- [ ] 分析日志，确定失败点

## 2. 修复阶段

### 2.1 修复 Agent 模块导入问题（如果诊断发现）
- [ ] 验证 `docker-compose.yml` 中 `backend` 服务的 `volumes` 包含 `- ./Agent:/Agent`
- [ ] 验证 Agent 目录在容器内存在且可访问
- [ ] 如果需要，修复 `agent_service.py` 中的路径配置

### 2.2 修复 MCP 服务器连接问题（如果诊断发现）
- [ ] 如果 MCP ECharts 服务器未运行，在 `docker-compose.yml` 中添加 `mcp-echarts` 服务：
  ```yaml
  mcp-echarts:
    image: node:18
    command: npx -y mcp-echarts -t sse -p 3033
    ports:
      - "3033:3033"
    networks:
      - dataagent-network
  ```
- [ ] 如果需要，更新 `Agent/sql_agent.py` 中的 MCP ECharts URL（如果不在 localhost）
- [ ] 验证 MCP Postgres 服务器可以通过 `npx` 启动（检查 Node.js 是否在容器内可用）

### 2.3 修复数据库连接问题（如果诊断发现）
- [ ] 验证 `database_url` 格式正确（PostgreSQL 连接字符串）
- [ ] 验证 Agent 的 `config.py` 正确读取 `database_url`
- [ ] 如果需要，修复 `agent_service.py` 中的 `database_url` 传递逻辑

### 2.4 改进错误处理
- [ ] 确保 `run_agent_query` 函数返回 `VisualizationResponse` 对象（即使失败，也要返回包含错误信息的对象）
- [ ] 改进 `convert_agent_response_to_query_response` 函数，处理 `agent_response` 为 `None` 的情况
- [ ] 在 `/api/v1/query` 端点中，如果 Agent 返回 `None` 或 `success=False`，记录详细错误信息

### 2.5 修复配置问题（如果诊断发现）
- [ ] 验证 DeepSeek API 密钥在环境变量中正确配置
- [ ] 验证 `Agent/config.py` 正确读取后端配置（`_get_backend_config()` 函数）
- [ ] 如果需要，修复配置读取逻辑

## 3. 验证阶段

### 3.1 功能验证
- [ ] 在前端发送一次查询（选择单个数据源，例如 `ecommerce_test_db`）
- [ ] 验证后端日志显示"使用 Agent 处理查询"
- [ ] 验证响应包含：
  - [ ] `generated_sql` 不为空
  - [ ] `results` 不为空（如果有数据）
  - [ ] `execution_result` 不为 null（如果成功）
  - [ ] `execution_result.chart_data` 不为空（如果生成了图表）

### 3.2 前端显示验证
- [ ] 验证前端正确显示 SQL 查询结果表格
- [ ] 验证前端正确显示图表（如果有）
- [ ] 验证前端正确显示 Agent 生成的解释文本

### 3.3 错误场景验证
- [ ] 测试无效的数据源 ID
- [ ] 测试无效的 SQL 查询（Agent 应该返回错误信息）
- [ ] 测试 MCP 服务器未运行的情况（应该返回清晰的错误信息）

## 4. 文档更新

### 4.1 更新诊断文档
- [ ] 记录诊断过程中发现的问题
- [ ] 记录修复方案
- [ ] 更新 `LIMITATIONS.md`（如果需要）

### 4.2 更新运行文档
- [ ] 更新 `README.md`，说明如何启动 MCP 服务器
- [ ] 更新 `docker-compose.yml` 注释，说明 MCP 服务器配置


