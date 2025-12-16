## Context
当前系统使用 MCP (Model Context Protocol) ECharts 服务来生成图表。该服务运行在独立的 Docker 容器中，通过 SSE (Server-Sent Events) 协议提供图表生成能力。后端 Agent 通过 LangGraph 工具调用机制与 MCP ECharts 服务通信。

## Goals / Non-Goals
- Goals:
  - 修复 MCP ECharts 服务连接问题，确保服务健康运行
  - 确保后端能正确调用图表生成服务并获取结果
  - 确保图表图片能正确返回给前端显示
- Non-Goals:
  - 不改变现有的图表生成架构（继续使用 MCP ECharts）
  - 不修改前端图表显示组件（前端已支持显示 chart_image）

## Decisions
- Decision: 使用 Docker 服务名进行容器间通信
  - 在 Docker 环境中，backend 容器通过 `http://mcp_echarts:3033/sse` 访问服务
  - 在本地开发环境中，使用 `http://localhost:3033/sse`
  - 通过环境变量 `MCP_ECHARTS_URL` 可覆盖默认配置
- Decision: 图表图片以 Base64 data URI 格式返回
  - 优点：无需额外的文件存储和 URL 管理
  - 缺点：响应体积较大，但可接受（图表通常 < 500KB）
  - 如果 MCP 返回 HTTP URL，直接使用 URL（适用于生产环境）

## Risks / Trade-offs
- Risk: MCP ECharts 服务不稳定导致图表生成失败
  - Mitigation: 添加重试机制和降级方案（仅返回表格，不显示图表）
- Risk: Base64 编码的图片数据过大影响 API 响应时间
  - Mitigation: 监控响应大小，如果超过阈值考虑使用文件存储 + URL 方案
- Risk: Docker 网络配置问题导致服务无法访问
  - Mitigation: 添加连接测试和健康检查，在启动时验证服务可达性

## Migration Plan
1. 修复 MCP ECharts 服务配置，确保健康检查通过
2. 验证后端能成功调用服务并获取图表数据
3. 更新 API 响应格式化逻辑，确保 chart_image 字段正确填充
4. 测试完整流程，确保前端能正确显示图表
5. 如果修复过程中发现架构问题，记录并计划后续改进

## Open Questions
- MCP ECharts 服务返回的图表数据格式是什么？（Base64？URL？文件路径？）
- 是否需要添加图表缓存机制以减少重复生成？
- 是否需要在图表生成失败时提供降级方案（例如使用前端 ECharts 库直接渲染）？

