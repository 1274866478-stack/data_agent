## MODIFIED Requirements

### Requirement: AI 助手数据准确性
AI 助手在回答数据查询问题时，SHALL 必须基于真实数据源返回准确的数据，禁止编造或使用示例数据。

#### Scenario: 文件数据源查询必须调用工具
- **WHEN** 用户查询文件数据源（Excel/CSV）中的数据
- **THEN** AI 必须先调用 `inspect_file` 工具查看文件结构
- **AND** AI 必须调用 `analyze_dataframe` 工具读取实际数据
- **AND** AI 必须基于工具返回的真实数据生成回答
- **AND** 如果未调用必要工具，系统 SHALL 自动拦截回答并返回错误消息

#### Scenario: SQL数据源查询必须调用工具
- **WHEN** 用户查询SQL数据库中的数据
- **THEN** AI 必须先调用 `list_tables` 工具查看表列表（如需要）
- **AND** AI 必须调用 `query` 或 `execute_sql_safe` 工具执行查询
- **AND** AI 必须基于工具返回的真实数据生成回答
- **AND** 如果未调用必要工具，系统 SHALL 自动拦截回答并返回错误消息

#### Scenario: 幻觉检测和拦截
- **WHEN** AI 生成的回答包含具体数据（如用户列表、统计数据等）
- **THEN** 系统 SHALL 检测是否包含假数据模式（如"用户1"、"用户2"、"Alice"、"Bob"等）
- **AND** 如果检测到假数据模式且未调用工具，系统 SHALL 自动拦截回答
- **AND** 系统 SHALL 返回用户友好的错误消息，说明需要调用工具查询数据
- **AND** 错误消息 SHALL 包含解决建议（如检查数据源连接、重新提问等）

#### Scenario: 工具调用失败时的错误处理
- **WHEN** 工具调用失败或返回"SYSTEM ERROR"
- **THEN** AI SHALL 停止生成答案
- **AND** 系统 SHALL 返回明确的错误消息给用户
- **AND** 错误消息 SHALL 说明工具调用失败的原因
- **AND** AI SHALL 禁止基于错误信息推测或编造数据

#### Scenario: 数据一致性验证
- **WHEN** AI 生成包含数据的回答
- **THEN** 系统 SHALL 验证回答中的数据是否与工具返回的数据一致
- **AND** 如果发现不一致，系统 SHALL 记录警告日志
- **AND** 系统 SHALL 优先使用工具返回的真实数据

## ADDED Requirements

### Requirement: 工具调用验证机制
系统 SHALL 在AI生成回答后验证是否调用了必要工具。

#### Scenario: 文件数据源工具调用验证
- **WHEN** 数据源类型为文件（Excel/CSV）
- **THEN** 系统 SHALL 验证是否调用了 `inspect_file` 工具
- **AND** 系统 SHALL 验证是否调用了 `analyze_dataframe` 工具
- **AND** 如果缺少任一必要工具调用，系统 SHALL 拦截回答并返回错误消息

#### Scenario: SQL数据源工具调用验证
- **WHEN** 数据源类型为SQL数据库
- **THEN** 系统 SHALL 验证是否调用了 `query` 或 `execute_sql_safe` 工具
- **AND** 如果未调用必要工具，系统 SHALL 拦截回答并返回错误消息

### Requirement: 幻觉检测模式
系统 SHALL 检测并拦截常见的假数据模式。

#### Scenario: 编号模式检测
- **WHEN** AI 回答包含"用户1"、"用户2"、"用户ID: 1"等编号模式
- **THEN** 系统 SHALL 检测这些模式
- **AND** 如果检测到编号模式且未调用工具，系统 SHALL 拦截回答

#### Scenario: 测试数据模式检测
- **WHEN** AI 回答包含常见的测试数据（如"Alice"、"Bob"、"Charlie"、"张三"、"李四"等）
- **THEN** 系统 SHALL 检测这些模式
- **AND** 如果检测到测试数据模式且未调用工具，系统 SHALL 拦截回答

#### Scenario: 连续列表模式检测
- **WHEN** AI 回答包含连续的编号列表（如"用户1、用户2、用户3"）
- **THEN** 系统 SHALL 检测这些模式
- **AND** 如果检测到连续列表模式且未调用工具，系统 SHALL 拦截回答

### Requirement: 增强的System Prompt规则
AI 助手的 System Prompt SHALL 包含严格的规则，禁止在没有调用工具的情况下生成数据。

#### Scenario: 强制工具调用规则
- **WHEN** System Prompt 被加载
- **THEN** Prompt SHALL 在开头包含最严格的规则
- **AND** Prompt SHALL 明确禁止在没有调用工具的情况下生成任何具体数据
- **AND** Prompt SHALL 明确禁止使用示例数据或编造数据
- **AND** Prompt SHALL 包含few-shot示例展示正确行为

#### Scenario: 错误处理规则
- **WHEN** System Prompt 被加载
- **THEN** Prompt SHALL 明确要求工具调用失败时必须明确告知用户
- **AND** Prompt SHALL 禁止基于错误信息推测或编造数据

