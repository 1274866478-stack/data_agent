# Change: 集成 Agent 文件夹到项目根目录

## Why

`Agent` 文件夹位于项目根目录下，包含一个完整的基于 LangGraph 和 MCP 协议的 SQL 智能查询代理系统。该文件夹目前是独立的，但实际上是项目的一部分，需要整合到项目结构中以确保：

1. **最终目标**：**在前端 AI 助手页面（`/ai-assistant`）中实现 Agent 的功能**，让用户通过前端界面使用 Agent 进行 SQL 查询和数据分析
2. **代码组织一致性**：将 Agent 代码整合到项目标准结构中，便于维护和开发
3. **依赖管理统一**：合并依赖项到后端的 `requirements.txt`，避免重复和版本冲突
4. **配置管理统一**：将 Agent 的配置整合到后端配置系统
5. **路径引用修复**：修复导入路径，确保代码能正常运行
6. **API 集成**：将 Agent 功能集成到后端 API，供前端 AI 助手调用

## What Changes

- **BREAKING**: 将 `Agent/` 文件夹移动到项目根目录（保持 `Agent/` 名称或重命名为更合适的名称）
- 合并 `Agent/requirements.txt` 的依赖到 `backend/requirements.txt`
- 更新 Agent 代码中的导入路径（从相对导入改为项目级导入）
- 整合 Agent 的配置管理到后端配置系统（`backend/src/app/core/config.py`）
- **将 DeepSeek 设置为默认 LLM 提供商**：在后端配置中添加 DeepSeek 支持，并将其设置为默认 LLM（替代当前的智谱 GLM）
- 更新或创建运行脚本，确保 Agent 可以独立运行或集成到后端服务中
- 处理虚拟环境（`Agent/venv/`）的迁移或清理

## Impact

- **受影响的规范**: 无（这是项目结构整合，不涉及功能变更）
- **受影响的代码**:
  - `Agent/` 文件夹下的所有 Python 文件（导入路径需要更新）
  - `backend/requirements.txt`（需要添加新依赖）
  - `backend/src/app/core/config.py`（需要添加 DeepSeek 配置，设置为默认 LLM）
  - `backend/src/app/services/llm_service.py`（更新默认 LLM 提供商为 DeepSeek）
  - `backend/src/app/api/v1/endpoints/query.py`（集成 Agent 功能，供前端 AI 助手调用）
  - 运行脚本（`Agent/run.py`, `Agent/run.bat`, `Agent/run.sh`）
  - `frontend/src/lib/api-client.ts`（可能需要更新类型定义以支持 Agent 响应格式，可选）
- **新增依赖**:
  - `langgraph>=0.2.0`
  - `langchain>=0.3.0`
  - `langchain-openai>=0.2.0`
  - `langchain-community>=0.3.0`
  - `langchain-mcp-adapters>=0.1.0`
  - `mcp>=1.0.0`
  - `pyecharts>=2.0.0`
  - `rich>=13.0.0`
- **环境要求**: 需要 Node.js 环境（用于运行 MCP Server）

