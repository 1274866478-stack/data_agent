## 1. 诊断和确认问题

- [ ] 1.1 确认 Docker 容器中确实缺少 Node.js/npm
- [ ] 1.2 检查 `backend/Dockerfile` 当前配置
- [ ] 1.3 验证错误发生在 MCP PostgreSQL 服务器启动时

## 2. 实施方案（选择方案三：混合方案）

### 2.1 更新 Dockerfile 安装 Node.js

- [ ] 2.1.1 在 `backend/Dockerfile` 中添加 Node.js 安装步骤
- [ ] 2.1.2 选择合适的 Node.js 版本（建议 LTS 版本）
- [ ] 2.1.3 验证安装后 `npx` 命令可用

### 2.2 改进错误处理

- [ ] 2.2.1 在 `agent_service.py` 的 `get_mcp_config()` 中添加 `npx` 命令可用性检查
- [ ] 2.2.2 在 `build_agent()` 中添加更详细的错误日志
- [ ] 2.2.3 在 `Agent/sql_agent.py` 的 `_get_or_create_agent()` 中添加错误处理
- [ ] 2.2.4 当 MCP 初始化失败时，提供清晰的错误信息给用户

### 2.3 优雅降级机制

- [ ] 2.3.1 检查 `DISABLE_MCP_TOOLS` 环境变量的处理逻辑
- [ ] 2.3.2 确保禁用 MCP 时，自定义工具能够正常工作
- [ ] 2.3.3 在错误处理中提示用户可以禁用 MCP 作为备选方案

## 3. 测试和验证

- [ ] 3.1 在 Docker 容器中验证 Node.js/npm 安装成功
- [ ] 3.2 验证 MCP PostgreSQL 服务器可以正常启动
- [ ] 3.3 测试 Agent 查询功能是否正常工作
- [ ] 3.4 测试禁用 MCP 时的降级机制
- [ ] 3.5 验证错误日志是否清晰易懂

## 4. 文档更新

- [ ] 4.1 更新 README 或相关文档，说明 Node.js 依赖
- [ ] 4.2 添加故障排查指南，说明如何处理 MCP 初始化失败
- [ ] 4.3 说明如何使用 `DISABLE_MCP_TOOLS` 环境变量

