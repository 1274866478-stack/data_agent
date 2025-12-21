# Change: 修复图表生成服务连接

## Why
当前 AI 助手在回答用户查询时，虽然 LLM 回复中声称"已生成折线图、柱状图"，但前端只显示表格，没有实际图表。原因是：
1. `mcp_echarts` Docker 服务状态为 unhealthy，无法正常响应图表生成请求
2. 后端 Agent 虽然配置了 MCP ECharts 连接，但可能因为服务不可用而静默失败
3. 图表图片没有正确生成或没有正确返回给前端（缺少 `chart_image` 字段）

## What Changes
- 诊断并修复 `mcp_echarts` Docker 服务的健康检查问题
- 确保后端 Agent 正确调用 MCP ECharts 服务生成图表
- 修复图表图片的生成、存储和返回流程，确保 `chart_image` 字段包含有效的 Base64 数据 URI 或 HTTP URL
- 添加错误处理和日志，当图表生成失败时给出明确提示
- 验证前端能正确接收并显示图表图片

## Impact
- Affected specs: ai-assistant 图表可视化能力
- Affected code:
  - `docker-compose.yml` (mcp_echarts 服务配置)
  - `Agent/Dockerfile.mcp` (MCP ECharts 容器配置)
  - `backend/src/app/services/agent/agent_service.py` (MCP 客户端配置和图表生成逻辑)
  - `backend/src/app/services/agent/data_transformer.py` (图表数据转换)
  - `backend/src/app/services/agent/response_formatter.py` (API 响应格式化，确保 chart_image 字段正确)
  - `backend/src/app/services/agent_service.py` (图表路径提取和 Base64 编码)


