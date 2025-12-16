## Change: 接入 AI 助手 Agent 图表能力到前端

## Why
当前 Agent 后端已经可以返回结构化数据和图表信息，但 AI 助手前端只展示纯文本回答，用户无法在对话中直接看到可视化结果，体验不完整。

## What Changes
- 扩展前端 `ChatQueryResponse` 和 `ChatMessage.metadata`，支持表格和图表元数据。
- 更新 `ApiClient.sendAgentQuery`，从 `/query` 响应中解析 Agent 的 `data/chart` 信息并映射到前端统一结构。
- 在 `useChatStore` 中将这些结构化结果挂到 assistant 消息的 `metadata`。
- 在 AI 助手页面增加查询结果视图组件，根据消息元数据渲染表格和图表。

## Impact
- Affected specs: ai-assistant 对话与可视化能力。
- Affected code:
  - `frontend/src/lib/api-client.ts`
  - `frontend/src/store/chatStore.ts`
  - `frontend/src/app/(app)/ai-assistant/page.tsx`
  - 新增若干前端可视化组件（放在 `components/chat/` 或类似目录）。



