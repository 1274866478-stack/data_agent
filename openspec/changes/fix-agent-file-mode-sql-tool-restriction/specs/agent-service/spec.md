## MODIFIED Requirements

### Requirement: Agent 文件模式工具限制
Agent 在处理文件数据源（Excel/CSV）时，必须严格限制工具使用，防止调用 SQL 工具导致系统崩溃。

当检测到数据源为文件类型时，Agent 必须：
1. 使用"核威慑"级别的系统指令，明确告知 SQL 工具已断开连接且会导致系统崩溃
2. 只能使用 `analyze_dataframe` 和 `inspect_file` 工具
3. 绝对禁止使用 `query`、`list_tables`、`get_schema` 等 SQL 相关工具
4. 系统指令必须包含 `SYSTEM ALERT`、`DISCONNECTED` 等强硬词汇，让 AI 认为 SQL 工具真的坏了

#### Scenario: 文件模式下成功使用文件工具
- **WHEN** 用户查询 Excel 文件数据
- **AND** 系统检测到数据源为文件类型
- **THEN** Agent 接收包含"核威慑"级别警告的系统指令
- **AND** Agent 调用 `inspect_file` 或 `analyze_dataframe` 工具
- **AND** Agent 不调用任何 SQL 工具
- **AND** 系统返回基于真实文件数据的准确答案

#### Scenario: 文件模式下阻止 SQL 工具调用
- **WHEN** 用户查询 Excel 文件数据
- **AND** 系统检测到数据源为文件类型
- **AND** Agent 尝试调用 `query` 工具
- **THEN** 系统指令中的警告应该足够强烈，阻止 Agent 调用 SQL 工具
- **AND** Agent 转而使用 `analyze_dataframe` 工具
- **AND** 系统不因类型错误而崩溃

#### Scenario: 系统指令注入验证
- **WHEN** 系统检测到文件模式
- **THEN** 系统指令必须包含以下关键元素：
  - `SYSTEM ALERT` 或 `DISCONNECTED` 警告
  - 明确说明 SQL 工具会导致系统崩溃
  - 强制要求使用 `analyze_dataframe` 或 `inspect_file`
- **AND** 系统记录完整的系统指令内容到日志

