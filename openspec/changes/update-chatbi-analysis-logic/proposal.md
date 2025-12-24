# Change: 升级 ChatBI 数据分析与可视化决策逻辑

## Why
当前 AI 在分析 SQL 查询结果时，缺乏基于数据特征（行数、列类型）的智能决策能力，导致"乱画图"或"不画图"的问题。用户需要 AI 能够根据数据形态自动判断是否需要可视化，以及选择合适的图表类型。

## What Changes
- **更新 System Prompt**：在二次 LLM 调用的 `analysis_messages` 中使用更详细的系统提示，明确数据分析师的核心协议和可视化逻辑
- **新增数据特征分析逻辑**：在 SQL 查询执行成功后、构建分析消息前，植入基于数据行数、列类型的决策逻辑
- **生成分析指令（analysis_directive）**：
  - 单行数据 → 禁止画图
  - 纯文本列表 → 禁止画图
  - 大数据量（>20行）→ 强制 Top 10
  - 时间序列数据 → 强制折线图
  - 分类对比数据 → 建议柱状图/饼图
- **注入决策指令到 User 消息**：将分析指令追加到发送给 AI 的用户消息中

## Impact
- Affected specs: `ai-assistant`
- Affected code: `backend/src/app/api/v1/endpoints/llm.py`
  - `_stream_response_generator` 方法中的二次 LLM 调用逻辑
  - System prompt 和 User message 构建逻辑




