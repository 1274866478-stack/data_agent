## 1. 后端实现

- [ ] 1.1 创建 `backend/src/app/services/agent/prompts.py` 文件，定义 `get_system_prompt()` 函数
- [ ] 1.2 在 System Prompt 中添加 ECharts JSON 输出指令，包括：
  - 何时应该生成图表（时间序列、对比数据等场景）
  - JSON 配置格式要求（必须包含 title, tooltip, xAxis, yAxis, series）
  - 标记格式要求（使用 `[CHART_START]` 和 `[CHART_END]` 包裹）
- [ ] 1.3 在 `backend/src/app/services/agent/agent_service.py` 的 `run_agent()` 函数中添加解析逻辑：
  - 使用正则表达式 `/\[CHART_START\]([\s\S]*?)\[CHART_END\]/` 提取 JSON
  - 验证 JSON 格式有效性
  - 将解析的 JSON 填充到 `VisualizationResponse.echarts_option` 字段
  - 从 `final_content` 中移除 JSON 部分，避免在文字回复中显示
- [ ] 1.4 确保 `backend/src/app/services/agent/response_formatter.py` 的 `format_api_response()` 函数正确返回 `echarts_option` 字段
- [ ] 1.5 添加错误处理：如果 JSON 解析失败，记录警告但不影响文字回复

## 2. 前端实现

- [ ] 2.1 在 `frontend/package.json` 中添加依赖：
  - `echarts`: "^5.4.0"
  - `echarts-for-react`: "^3.0.2"
- [ ] 2.2 运行 `npm install` 安装新依赖
- [ ] 2.3 创建 `frontend/src/components/chat/EChartsRenderer.tsx` 组件：
  - 接收 `echartsOption` prop（类型为 `Record<string, any> | null`）
  - 使用 `echarts-for-react` 渲染图表
  - 处理加载状态和错误状态
  - 添加响应式尺寸调整
- [ ] 2.4 创建 `frontend/src/utils/chartParser.ts` 工具函数：
  - 实现 `extractEChartsOption(content: string): Record<string, any> | null` 函数
  - 使用正则表达式 `/\[CHART_START\]([\s\S]*?)\[CHART_END\]/` 提取 JSON
  - 解析 JSON 并验证格式
  - 返回解析后的配置对象或 null
- [ ] 2.5 更新 `frontend/src/app/(app)/ai-assistant/page.tsx`：
  - 在消息渲染逻辑中，使用 `chartParser.extractEChartsOption()` 从 `message.content` 提取配置
  - 如果提取成功，渲染 `EChartsRenderer` 组件
  - 从显示的文本内容中移除 JSON 部分（可选，或保留标记但隐藏）
- [ ] 2.6 更新 `frontend/src/components/chat/MessageList.tsx`（如果使用）：
  - 添加相同的图表提取和渲染逻辑
- [ ] 2.7 更新 `frontend/src/store/chatStore.ts` 的类型定义（如果需要）：
  - 确保 `ChatMessage.metadata` 可以包含 `echarts_option` 字段

## 3. 测试和验证

- [ ] 3.1 测试后端解析逻辑：
  - 模拟包含 `[CHART_START]...{...}[CHART_END]` 的 LLM 回复
  - 验证 JSON 正确提取并填充到 `echarts_option`
  - 验证文字回复中 JSON 部分被移除
- [ ] 3.2 测试前端渲染：
  - 输入测试查询"分析今年的收入趋势"
  - 验证页面显示文字分析
  - 验证页面渲染折线图
  - 验证图表可以正常交互（缩放、悬停等）
- [ ] 3.3 测试错误处理：
  - 测试无效 JSON 格式的处理
  - 测试缺少必需字段的配置
  - 验证错误情况下不影响文字回复显示
- [ ] 3.4 测试向后兼容性：
  - 验证现有的 `chart_image` 方式仍然工作
  - 验证没有图表配置时页面正常显示

## 4. 文档更新

- [ ] 4.1 更新 `backend/src/app/services/agent/README.md`（如果存在）或创建文档说明新的图表输出协议
- [ ] 4.2 在代码中添加注释说明 `[CHART_START]` 和 `[CHART_END]` 标记的用途

