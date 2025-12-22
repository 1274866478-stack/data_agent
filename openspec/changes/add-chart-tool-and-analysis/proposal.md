# Change: 恢复 ChatBI 流式输出中的数据分析和可视化能力

## Why

**这是一个功能回归问题**，而非新增功能。

在实现流式输出之前，ChatBI 项目已经具备以下能力：
- ✅ 使用 `run_agent` 函数处理查询
- ✅ 通过 MCP ECharts 工具生成图表
- ✅ 从 LLM 响应中提取 `[CHART_START]...[CHART_END]` 标记的 ECharts JSON
- ✅ 返回 `VisualizationResponse` 对象（包含 `echarts_option`）

**流式输出改造后，这些功能丢失的原因**：

1. **绕过了原有 Agent 架构**：新的 `/api/v1/llm/chat/completions` 接口直接调用 `llm_service.chat_completion`，没有使用 `agent_service.run_agent`

2. **System Prompt 被简化**：新接口的 prompt 只关注 SQL 查询，缺少图表生成指令（对比原有 `prompts.py` 中 500+ 行的完整 prompt）

3. **工具列表不完整**：只定义了 `execute_sql`，缺少图表工具

4. **响应处理缺失**：没有从 LLM 响应中提取 `[CHART_START]...[CHART_END]` 标记

## What Changes

### 方案选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A: 恢复 Agent 调用** | 复用现有代码，改动小 | 可能影响流式性能 |
| **B: 整合图表逻辑到流式接口** | 性能好，架构清晰 | 需要迁移较多代码 |
| **C: 使用 `[CHART_START]` 标记** | 简单，无需新工具 | 依赖 LLM 格式一致性 |

**推荐方案 C + 部分 B**：
1. 复用原有 `prompts.py` 中的系统提示（要求 AI 输出 `[CHART_START]...[CHART_END]`）
2. 在 `_stream_response_generator` 中检测并提取 ECharts JSON
3. 通过 `tool_result` 事件将图表配置发送到前端

### 具体修改

1. **复用原有 System Prompt** (`llm.py`)
   - 从 `prompts.py` 导入 `get_system_prompt()` 或关键部分
   - 确保包含图表生成指令

2. **提取 ECharts 配置** (`llm.py`)
   - 检测 `[CHART_START]...[CHART_END]` 标记
   - 解析 JSON 配置
   - 通过流式事件发送到前端

3. **前端渲染恢复** (`chatStore.ts`)
   - 在 `onToolResult` 中处理 ECharts 配置
   - 存储到消息 metadata 中

## Impact

- **受影响的代码**:
  - `backend/src/app/api/v1/endpoints/llm.py` - 恢复图表提取逻辑
  - `backend/src/app/services/agent/prompts.py` - 复用现有 prompt
  - `frontend/src/store/chatStore.ts` - 恢复图表渲染

## 原有实现参考

### 已有的图表生成模块

```
backend/src/app/services/agent/
├── agent_service.py      # run_agent(enable_echarts=True)
├── data_transformer.py   # sql_result_to_echarts_data()
├── models.py             # VisualizationResponse, ChartConfig
├── prompts.py            # get_system_prompt() - 完整的图表生成指令
└── response_formatter.py # format_api_response()
```

### 关键代码位置

1. **ECharts 提取逻辑** (`agent_service.py:1595-1648`)
   ```python
   # Extract ECharts JSON configuration from LLM response
   echarts_option_from_text = None
   # ... 检测 [CHART_START]...[CHART_END] 标记
   ```

2. **图表生成指令** (`prompts.py:298-301`)
   ```
   第四步：必须生成图表配置：
   - 在文字回复的最后，必须包含 [CHART_START]...[CHART_END] 标记的 ECharts JSON 配置
   ```

3. **VisualizationResponse** (`models.py:52-67`)
   ```python
   class VisualizationResponse(BaseModel):
       echarts_option: Optional[Dict[str, Any]] = Field(default=None)
   ```
