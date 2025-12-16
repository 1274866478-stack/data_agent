## 1. Implementation
- [ ] 1.1 扩展前端 `ChatQueryResponse` / Agent 相关类型，加入表格和图表字段（保持向后兼容）。
- [ ] 1.2 更新 `ApiClient.sendAgentQuery`，从 `/query` 响应中解析 `data` / `chart` / `execution_result.chart_data`，填充到新的字段。
- [ ] 1.3 在 `useChatStore` 的 `_sendOnlineMessage` 中，将结构化结果挂到 assistant 消息 `metadata`。
- [ ] 1.4 新增一个查询结果视图组件（表格 + 图表），放在合适的前端目录。
- [ ] 1.5 在 `AIAssistantPage` 的消息渲染逻辑里接入该组件，仅对带有元数据的 assistant 消息渲染可视化。
- [ ] 1.6 手动验证包含图表的典型问题在 AI 助手中能展示文本 + 图表，且无图表时行为与现在保持一致。



