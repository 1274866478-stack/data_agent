# Change: 修复 Agent 文件模式下调用 SQL 工具导致崩溃问题

## Why

根据 Gemini 的诊断报告，发现了一个严重的系统崩溃问题：

**问题现象**：
1. 路由逻辑成功：系统正确识别了文件数据源（xlsx），并注入了文件模式的提示词
2. Agent "叛逆"：尽管在 Prompt 中写了"严禁使用 SQL 工具"，但 Agent 依然调用了 `query` 工具（SQL 工具），而不是 `analyze_dataframe`（Excel 专用工具）
3. 崩溃原因：`query` 工具执行后返回了数据库里所有的系统表名（`api_keys`, `audit_logs` 等），这是一个 JSON 列表（List），但 DeepSeek 的 API 接口期望接收一个字符串（String），导致 `400 Bad Request` 错误：`openai.BadRequestError: ... invalid type: sequence, expected a string`
4. 幻觉产生：由于 Agent 崩溃，系统触发了 Fallback（兜底机制），LLM 在没有数据的情况下编造了标准占位符数据（Alice/Bob 是编程界最常用的测试名）

**根本原因**：
- 仅通过 Prompt 警告无法有效阻止 Agent 调用 SQL 工具
- 需要在代码层面进行更激进的工具限制，或者使用"核威慑"级别的警告

这是一个严重的数据准确性和系统稳定性问题，会导致：
- 系统崩溃（400 Bad Request）
- 用户收到虚假数据（幻觉）
- 系统可信度受损

## What Changes

### 优先级1：增强系统指令（System Instruction）
- 在 `backend/src/app/services/agent_service.py` 的 `run_agent_query` 函数中，将文件模式的系统指令升级为"核威慑"级别
- 使用 `SYSTEM ALERT`、`DISCONNECTED` 等强硬词汇，让 AI 认为 SQL 工具真的坏了
- 明确说明使用 `query` 工具会导致系统立即崩溃

### 优先级2：改进错误处理
- 增强对工具调用错误的捕获和处理
- 当检测到文件模式下调用了 SQL 工具时，提供更明确的错误消息

### 优先级3：增强日志记录
- 记录文件模式检测的详细信息
- 记录工具调用决策过程
- 记录系统指令注入的完整内容

## Impact

- **受影响的功能**：AI 助手查询功能（文件数据源模式）
- **受影响的代码**：
  - `backend/src/app/services/agent_service.py` - Agent 服务（系统指令增强）
- **影响范围**：所有使用文件数据源（Excel/CSV）的查询场景
- **预期效果**：
  - Agent 在文件模式下不再调用 SQL 工具
  - 系统不再因类型错误而崩溃
  - 用户能够获得基于真实文件数据的准确答案
  - 消除 Alice/Bob 等幻觉数据

