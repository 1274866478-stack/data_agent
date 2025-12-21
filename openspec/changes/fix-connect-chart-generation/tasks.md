## 1. 诊断和修复 MCP ECharts 服务
- [ ] 1.1 检查 `mcp_echarts` 容器日志，诊断 unhealthy 原因
- [ ] 1.2 修复 Dockerfile.mcp 或 docker-compose.yml 中的配置问题
- [ ] 1.3 验证服务健康检查能通过（curl http://localhost:3033/sse）
- [ ] 1.4 确保服务在 Docker 网络中可以正常访问（backend 容器能访问 mcp_echarts:3033）

## 2. 修复后端图表生成流程
- [ ] 2.1 检查 `get_mcp_config` 函数中的 ECharts URL 配置是否正确（Docker 环境使用服务名，本地使用 localhost）
- [ ] 2.2 验证 Agent 在 `enable_echarts=True` 时能正确调用 MCP ECharts 工具
- [ ] 2.3 修复图表图片的获取逻辑（从 MCP 工具调用结果中提取图片数据）
- [ ] 2.4 确保图表数据正确转换为 Base64 data URI 或可访问的 HTTP URL

## 3. 修复 API 响应格式化
- [ ] 3.1 检查 `format_api_response` 函数，确保 `chart.chart_image` 字段被正确填充
- [ ] 3.2 验证 `/query` 端点返回的响应中包含有效的 `chart_image` 字段
- [ ] 3.3 添加错误处理：当图表生成失败时，返回明确的错误信息而不是静默失败

## 4. 测试和验证
- [ ] 4.1 测试 MCP ECharts 服务能正常响应图表生成请求
- [ ] 4.2 测试后端 Agent 查询能成功生成图表并返回 `chart_image`
- [ ] 4.3 测试前端能正确接收并显示图表图片
- [ ] 4.4 验证完整流程：用户提问 → Agent 生成图表 → 前端显示图表


