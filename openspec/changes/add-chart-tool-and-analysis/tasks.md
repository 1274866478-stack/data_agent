# 任务清单：恢复 ChatBI 流式输出中的数据分析和可视化能力

## 前提：这是功能恢复，不是新增功能

原有代码位置：
- `backend/src/app/services/agent/agent_service.py` - ECharts 提取逻辑
- `backend/src/app/services/agent/prompts.py` - 完整的系统提示
- `backend/src/app/services/agent/data_transformer.py` - 数据转换
- `backend/src/app/services/agent/models.py` - VisualizationResponse

---

## 1. 恢复 System Prompt（后端）

### 1.1 导入原有 Prompt
- [ ] 1.1.1 在 `llm.py` 中导入 `prompts.py` 的 `get_system_prompt()` 函数
- [ ] 1.1.2 或者复制图表相关的核心指令到新 prompt 中

### 1.2 更新 `_stream_response_generator` 中的 system_message
- [ ] 1.2.1 添加图表生成工作流指令
- [ ] 1.2.2 添加 `[CHART_START]...[CHART_END]` 输出格式要求
- [ ] 1.2.3 添加数据分析步骤要求

---

## 2. 恢复 ECharts 提取逻辑（后端）

### 2.1 检测 `[CHART_START]...[CHART_END]` 标记
- [ ] 2.1.1 在流式响应收集完成后，检测标记
- [ ] 2.1.2 提取标记内的 JSON 字符串
- [ ] 2.1.3 解析 JSON 为 dict

### 2.2 发送图表配置到前端
- [ ] 2.2.1 创建 `chart_config` 类型的流式事件
- [ ] 2.2.2 将 ECharts 配置通过 SSE 发送
- [ ] 2.2.3 从最终文本中移除 `[CHART_START]...[CHART_END]` 块

### 2.3 参考原有实现
- [ ] 2.3.1 参考 `agent_service.py:1595-1648` 的 ECharts 提取逻辑
- [ ] 2.3.2 复用或适配 `data_transformer.py` 的转换函数

---

## 3. 恢复前端图表渲染

### 3.1 处理 `chart_config` 事件
- [ ] 3.1.1 在 `chatStore.ts` 的回调中添加 `onChartConfig` 处理
- [ ] 3.1.2 将 ECharts 配置存储到消息 `metadata.echarts_option`

### 3.2 渲染 ECharts 图表
- [ ] 3.2.1 检查消息组件是否已支持 `echarts_option` 渲染
- [ ] 3.2.2 如需要，恢复 ECharts 组件集成

---

## 4. 测试验证

### 4.1 功能恢复测试
- [ ] 4.1.1 测试 "分析销量趋势并画图" 场景
- [ ] 4.1.2 验证 ECharts 图表正确渲染
- [ ] 4.1.3 验证流式输出过程中的体验

### 4.2 回归测试
- [ ] 4.2.1 确保纯文本查询不受影响
- [ ] 4.2.2 确保 SQL 执行功能正常
- [ ] 4.2.3 确保错误处理正常

---

## 快速恢复路径（最小改动）

如果时间紧迫，可以只做以下步骤：

1. **复制 prompt 中的图表指令** 到 `llm.py` 的 system_message
2. **添加 ECharts 提取正则** 在流式完成后检测
3. **通过 `tool_result` 事件发送** 图表配置

这样可以最快恢复功能，后续再做优化。
