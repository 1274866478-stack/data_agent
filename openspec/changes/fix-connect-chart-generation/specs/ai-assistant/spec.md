## MODIFIED Requirements
### Requirement: AI 助手图表可视化
AI 助手在回答数据分析查询时，SHALL 能够生成并显示可视化图表（折线图、柱状图等）。

#### Scenario: 用户请求生成趋势图表
- **WHEN** 用户提问"基于 orders 表，按 order_date 汇总今年每月的销售额，并生成趋势"
- **THEN** AI 助手返回文本分析、数据表格和图表图片
- **AND** 图表图片通过 `chart.chart_image` 字段返回（Base64 data URI 或 HTTP URL）
- **AND** 前端正确显示图表图片在消息气泡中

#### Scenario: 图表生成服务不可用时的降级处理
- **WHEN** MCP ECharts 服务不可用或图表生成失败
- **THEN** AI 助手仍然返回文本分析和数据表格
- **AND** `chart.chart_image` 字段为 null 或缺失
- **AND** 前端仅显示表格，不显示图表（不报错）

#### Scenario: 图表生成成功但图片数据无效
- **WHEN** MCP ECharts 服务返回了响应，但图片数据格式不正确
- **THEN** 后端记录错误日志
- **AND** API 响应中 `chart.chart_image` 为 null
- **AND** 前端仅显示表格，不显示图表


