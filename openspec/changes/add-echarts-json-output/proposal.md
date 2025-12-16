# Change: 添加 ECharts JSON 配置输出功能

## Why

当前 ChatBI 项目中，Agent 能够查询数据并返回文字总结，但无法生成可视化图表。虽然后端已经支持通过 MCP ECharts 服务生成图表图片，但这种方式存在以下问题：

1. **依赖外部服务**：需要 MCP ECharts 服务运行，增加了系统复杂性和故障点
2. **静态图片限制**：生成的图片无法交互，用户体验较差
3. **前端渲染能力未充分利用**：前端已有图表渲染基础设施，但未充分利用

通过让 LLM 直接输出 ECharts JSON 配置，前端可以直接渲染交互式图表，提升用户体验并降低系统复杂度。

## What Changes

- **新增通信协议**：定义 `[CHART_START]` 和 `[CHART_END]` 标记，用于在 LLM 回复中标识 ECharts JSON 配置
- **修改 Agent System Prompt**：在 `backend/src/app/services/agent/prompts.py`（需要创建）中添加指令，要求 LLM 在适合可视化时输出 ECharts JSON 配置
- **后端解析逻辑**：在 `backend/src/app/services/agent/agent_service.py` 中添加解析逻辑，从 LLM 回复中提取 ECharts 配置并填充到 `echarts_option` 字段
- **前端依赖安装**：在 `frontend/package.json` 中添加 `echarts` 和 `echarts-for-react` 依赖
- **前端图表组件**：创建或更新 `frontend/src/components/chat/EChartsRenderer.tsx`，从消息文本中提取并渲染 ECharts 图表
- **前端消息展示更新**：更新 `frontend/src/app/(app)/ai-assistant/page.tsx` 和 `frontend/src/components/chat/MessageList.tsx`，集成 ECharts 渲染组件
- **API 响应格式**：确保 `backend/src/app/services/agent/response_formatter.py` 正确返回 `echarts_option` 字段

## Impact

- **受影响的规范**: `ai-assistant` 图表可视化能力
- **受影响的代码**:
  - `backend/src/app/services/agent/prompts.py`（新建，定义 System Prompt）
  - `backend/src/app/services/agent/agent_service.py`（添加 JSON 解析逻辑）
  - `backend/src/app/services/agent/response_formatter.py`（确保 echarts_option 正确返回）
  - `frontend/package.json`（添加 ECharts 依赖）
  - `frontend/src/components/chat/EChartsRenderer.tsx`（新建，图表渲染组件）
  - `frontend/src/app/(app)/ai-assistant/page.tsx`（集成图表渲染）
  - `frontend/src/components/chat/MessageList.tsx`（集成图表渲染）
  - `frontend/src/store/chatStore.ts`（可能需要更新类型定义）
- **新增依赖**:
  - `echarts` (前端)
  - `echarts-for-react` (前端)
- **向后兼容性**: 保持对现有 `chart_image` 字段的支持，新功能作为增强添加

