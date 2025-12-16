## MODIFIED Requirements

### Requirement: AI 助手图表可视化
AI 助手在回答数据分析查询时，SHALL 能够生成并显示交互式 ECharts 图表。

#### Scenario: LLM 输出 ECharts JSON 配置
- **WHEN** 用户提问适合可视化的问题（如"分析今年的收入趋势"）
- **THEN** LLM 在文字回复中包含 ECharts JSON 配置，格式为 `[CHART_START]{...}[CHART_END]`
- **AND** JSON 配置包含必需的字段：title, tooltip, xAxis, yAxis, series
- **AND** 后端从回复中提取 JSON 并填充到 `echarts_option` 字段
- **AND** 文字回复中不包含 JSON 配置的原始文本（已移除标记和 JSON）

#### Scenario: 前端渲染交互式图表
- **WHEN** 前端接收到包含 ECharts JSON 配置的消息
- **THEN** 前端从消息文本中提取 JSON 配置（使用正则表达式 `/\[CHART_START\]([\s\S]*?)\[CHART_END\]/`）
- **AND** 前端使用 `echarts-for-react` 渲染交互式图表
- **AND** 图表显示在文字分析下方
- **AND** 用户可以与图表交互（缩放、悬停查看数据点等）

#### Scenario: 图表配置解析失败时的降级处理
- **WHEN** LLM 输出的 JSON 格式不正确或解析失败
- **THEN** 后端记录警告日志但不影响文字回复
- **AND** 前端捕获解析错误并显示友好的错误提示（可选）
- **AND** 页面正常显示文字分析，不显示图表
- **AND** 不导致页面崩溃或错误

#### Scenario: 向后兼容性
- **WHEN** 消息中包含 `chart.chart_image` 字段（现有方式）
- **THEN** 前端优先显示 `chart_image` 图片
- **AND** 如果同时存在 `echarts_option`，可以选择显示交互式图表（优先级可配置）
- **AND** 如果只有 `echarts_option` 没有 `chart_image`，显示交互式图表

#### Scenario: 多种图表类型支持
- **WHEN** LLM 根据数据特征决定图表类型（折线图、柱状图、饼图等）
- **THEN** LLM 输出对应类型的 ECharts 配置
- **AND** 前端能够正确渲染各种类型的图表
- **AND** 图表配置符合 ECharts 官方规范

## ADDED Requirements

### Requirement: ECharts JSON 配置协议
系统 SHALL 定义并使用 `[CHART_START]` 和 `[CHART_END]` 标记来标识 LLM 回复中的 ECharts JSON 配置。

#### Scenario: 标记格式
- **WHEN** LLM 需要输出图表配置
- **THEN** JSON 配置必须包裹在 `[CHART_START]` 和 `[CHART_END]` 标记之间
- **AND** JSON 必须是有效的 JSON 格式
- **AND** JSON 不能包含在 Markdown 代码块中（避免被 Markdown 渲染器处理）

### Requirement: System Prompt 图表输出指令
Agent 的 System Prompt SHALL 包含明确的指令，指导 LLM 在适合可视化时输出 ECharts JSON 配置。

#### Scenario: 指令内容
- **WHEN** System Prompt 被加载
- **THEN** Prompt 包含以下指令：
  - 何时应该生成图表（时间序列、对比数据等场景）
  - JSON 配置格式要求（必须包含 title, tooltip, xAxis, yAxis, series）
  - 标记格式要求（使用 `[CHART_START]` 和 `[CHART_END]` 包裹）
  - 不要将 JSON 包裹在 Markdown 代码块中

### Requirement: 前端 ECharts 渲染组件
系统 SHALL 提供前端组件用于渲染从消息文本中提取的 ECharts 配置。

#### Scenario: 组件功能
- **WHEN** 组件接收到 ECharts 配置对象
- **THEN** 组件使用 `echarts-for-react` 渲染图表
- **AND** 组件处理加载状态
- **AND** 组件处理错误状态（配置无效时显示友好提示）
- **AND** 组件支持响应式尺寸调整

