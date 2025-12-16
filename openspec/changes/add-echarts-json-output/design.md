# Design: ECharts JSON 配置输出功能

## Context

当前系统使用 MCP ECharts 服务生成图表图片，但这种方式存在依赖外部服务、无法交互等问题。本设计通过让 LLM 直接输出 ECharts JSON 配置，前端直接渲染交互式图表。

## Goals / Non-Goals

### Goals
- LLM 能够在回复中输出 ECharts JSON 配置
- 前端能够从消息文本中提取并渲染图表
- 保持向后兼容，不影响现有的 `chart_image` 方式
- 提供良好的错误处理，确保解析失败不影响文字回复

### Non-Goals
- 不替换现有的 MCP ECharts 服务（两种方式可以共存）
- 不强制要求所有查询都生成图表（由 LLM 根据查询内容决定）
- 不实现复杂的图表类型推断（由 LLM 根据数据特征决定图表类型）

## Decisions

### Decision 1: 使用标记包裹 JSON 配置

**选择**: 使用 `[CHART_START]` 和 `[CHART_END]` 标记包裹 JSON 配置

**理由**:
- 简单明确，易于正则表达式提取
- 不会与 Markdown 语法冲突
- LLM 容易理解和遵循

**替代方案考虑**:
- 使用 Markdown 代码块：可能被 Markdown 渲染器处理，提取困难
- 使用特殊 JSON Schema：需要额外的解析逻辑，复杂度高
- 使用结构化输出：需要修改 LLM 调用方式，影响范围大

### Decision 2: 在 System Prompt 中指导 LLM 输出格式

**选择**: 在 System Prompt 中添加明确的指令，要求 LLM 在适合可视化时输出 ECharts JSON

**理由**:
- 不需要修改 LLM 调用方式，实现简单
- 可以灵活调整指令，适应不同场景
- 与现有架构兼容

**替代方案考虑**:
- 使用 Function Calling：需要定义复杂的 Schema，实现复杂
- 使用结构化输出：需要 LLM 支持，可能不兼容所有模型

### Decision 3: 前端从消息文本中提取配置

**选择**: 前端在渲染消息时，从 `message.content` 中提取 ECharts 配置

**理由**:
- 不需要修改 API 响应格式（虽然也可以从 `echarts_option` 字段获取）
- 保持灵活性，支持直接从 LLM 回复中提取
- 实现简单，不需要后端额外处理

**替代方案考虑**:
- 后端提取后通过 `echarts_option` 字段传递：需要后端解析，增加复杂度
- 混合方式：前端优先从 `echarts_option` 获取，如果没有则从文本提取

### Decision 4: 使用 echarts-for-react 渲染

**选择**: 使用 `echarts-for-react` 作为 React 封装

**理由**:
- 官方推荐的 React 集成方式
- 提供 TypeScript 类型支持
- 自动处理组件生命周期和尺寸调整

**替代方案考虑**:
- 直接使用 ECharts：需要手动处理 React 集成，代码复杂
- 使用其他图表库（如 recharts）：项目已有 recharts，但 ECharts 功能更强大

## Risks / Trade-offs

### Risk 1: LLM 输出格式不一致

**风险**: LLM 可能不严格按照指令输出，导致解析失败

**缓解措施**:
- 在 System Prompt 中提供明确的示例
- 实现容错解析，支持多种格式变体
- 解析失败时不影响文字回复显示

### Risk 2: JSON 格式错误

**风险**: LLM 输出的 JSON 可能格式不正确，导致前端渲染失败

**缓解措施**:
- 后端和前端都进行 JSON 验证
- 使用 try-catch 捕获解析错误
- 提供友好的错误提示

### Risk 3: 性能影响

**风险**: 在消息文本中搜索和解析 JSON 可能影响性能

**缓解措施**:
- 使用高效的正则表达式
- 只在消息渲染时解析一次，结果可以缓存
- 对于长消息，可以优化搜索范围

## Migration Plan

### Phase 1: 后端实现
1. 创建 `prompts.py` 文件，定义 System Prompt
2. 在 `agent_service.py` 中添加解析逻辑
3. 测试后端解析功能

### Phase 2: 前端实现
1. 安装 ECharts 依赖
2. 创建图表渲染组件
3. 集成到消息展示组件
4. 测试前端渲染功能

### Phase 3: 集成测试
1. 端到端测试完整流程
2. 测试错误处理
3. 验证向后兼容性

### Rollback Plan
- 如果出现问题，可以：
  1. 移除 System Prompt 中的图表输出指令
  2. 前端禁用图表提取逻辑
  3. 回退到仅使用 `chart_image` 的方式

## Open Questions

1. **是否需要支持多种图表库？** 当前选择 ECharts，但项目已有 recharts。是否需要统一？
   - **决定**: 先实现 ECharts，后续可以根据需要添加 recharts 支持

2. **图表配置的复杂度？** LLM 应该输出完整的 ECharts 配置还是简化配置？
   - **决定**: 要求输出完整的配置，包括 title, tooltip, xAxis, yAxis, series 等必需字段

3. **是否需要图表类型验证？** 是否需要在后端验证图表类型是否与数据匹配？
   - **决定**: 暂不实现，由 LLM 根据数据特征决定，前端直接渲染

