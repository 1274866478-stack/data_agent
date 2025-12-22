## ADDED Requirements

### Requirement: 流式AI助手响应
系统SHALL支持流式返回AI助手的回答内容，允许用户实时看到生成过程。

#### Scenario: 用户发送消息后实时看到回答
- **WHEN** 用户发送消息到AI助手
- **THEN** 系统立即开始流式返回回答内容
- **AND** 用户界面实时更新显示新生成的内容
- **AND** 用户可以看到回答的生成过程，无需等待完整回答

#### Scenario: 流式响应包含思考过程
- **WHEN** AI模型支持思考模式（thinking mode）
- **THEN** 系统SHALL流式返回思考过程和正式回答
- **AND** 前端SHALL区分并正确显示思考过程和正式回答

#### Scenario: 流式响应中的SQL执行和结构化数据
- **WHEN** AI回答中包含SQL查询或图表配置
- **THEN** 系统SHALL通过 `tool_input` 事件类型流式返回SQL代码
- **AND** 系统SHALL通过 `tool_output` 事件类型流式返回查询结果或ECharts配置
- **AND** 前端SHALL区分并正确渲染SQL代码块和结构化数据
- **AND** 系统SHALL自动执行SQL并返回结果

#### Scenario: 流式响应错误处理
- **WHEN** 流式响应过程中发生错误
- **THEN** 系统SHALL发送错误事件
- **AND** 前端SHALL显示错误信息
- **AND** 已生成的部分内容SHALL保留

#### Scenario: 连接中断和用户取消处理
- **WHEN** 流式响应过程中连接中断
- **THEN** 系统SHALL检测中断
- **AND** 前端SHALL显示连接中断提示
- **AND** 已生成的内容SHALL保留
- **AND** 用户SHALL可以重试或继续对话

#### Scenario: 用户手动中断流式响应
- **WHEN** 用户点击"停止生成"按钮
- **THEN** 系统SHALL立即中断流式响应（使用AbortController）
- **AND** 前端SHALL停止接收新的数据块
- **AND** 已生成的内容SHALL保留并标记为已中断
- **AND** 用户SHALL可以继续对话或重新发送消息

#### Scenario: 流式响应中的Markdown和图表渲染
- **WHEN** 流式传输包含Markdown代码块或JSON配置
- **THEN** 前端SHALL处理不完整的Markdown语法（如未闭合的代码块）
- **AND** 前端SHALL使用流式JSON解析器处理不完整的JSON字符串
- **AND** 前端SHALL防止因不完整内容导致的布局跳动或渲染错误
- **AND** 图表组件SHALL在JSON完整后正确渲染

## MODIFIED Requirements

### Requirement: AI助手聊天响应
系统SHALL支持流式和非流式两种响应模式，默认使用流式模式以提升用户体验。

#### Scenario: 流式模式响应
- **WHEN** 用户发送消息且系统支持流式模式
- **THEN** 系统SHALL使用流式模式返回回答
- **AND** 响应SHALL通过Server-Sent Events (SSE)格式传输
- **AND** 每个数据块SHALL包含类型标识（content, thinking, tool_input, tool_output, error, done）
- **AND** 前端SHALL支持通过AbortSignal中断流式响应

#### Scenario: 非流式模式降级
- **WHEN** 流式模式不可用或用户明确选择非流式模式
- **THEN** 系统SHALL降级到非流式模式
- **AND** 系统SHALL等待完整回答生成后返回
- **AND** 用户体验SHALL与当前实现保持一致

