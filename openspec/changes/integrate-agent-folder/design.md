# 集成 Agent 文件夹 - 技术设计文档

## Context

`Agent/` 文件夹包含一个基于 LangGraph 和 MCP 协议的 SQL 智能查询代理系统。该文件夹目前位于项目根目录，但需要整合到项目结构中以确保代码组织一致性和依赖管理统一。

## Goals / Non-Goals

### Goals
- 将 Agent 代码整合到项目标准结构中
- 统一依赖管理，避免版本冲突
- 统一配置管理
- 修复导入路径，确保代码正常运行
- 保持 Agent 的独立运行能力（如果需要）

### Non-Goals
- 不改变 Agent 的核心功能
- 不重构 Agent 的内部架构
- 不强制将 Agent 集成到后端服务中（保持可选）

## Decisions

### Decision 1: Agent 文件夹位置
**决策**: 保持 `Agent/` 文件夹在项目根目录

**理由**:
- Agent 是一个独立可运行的服务，不是后端的一部分
- 根目录位置便于独立运行和维护
- 避免与后端代码结构混淆

**替代方案**:
- 移动到 `backend/src/app/agent/` - 会与后端代码混合，不利于独立运行
- 移动到 `backend/agent/` - 可能造成混淆，因为 Agent 不是后端的一部分

### Decision 2: 配置管理策略
**决策**: 创建配置适配器，允许 Agent 使用后端配置系统，同时保持独立配置能力

**理由**:
- Agent 需要独立运行，不能完全依赖后端配置
- 统一配置管理可以减少重复和环境变量管理负担
- 适配器模式提供灵活性

**实现方式**:
- 保留 `Agent/config.py` 作为主要配置入口
- 如果检测到后端配置系统可用，优先使用后端配置
- 否则使用 Agent 自己的配置加载机制

### Decision 3: 依赖管理策略
**决策**: 合并所有依赖到 `backend/requirements.txt`，Agent 使用后端的依赖环境

**理由**:
- 避免依赖重复和版本冲突
- 简化环境管理
- 如果 Agent 需要独立运行，可以创建独立的虚拟环境并安装相同依赖

**替代方案**:
- 保持独立的 `Agent/requirements.txt` - 会导致依赖重复和版本冲突风险

### Decision 4: 虚拟环境处理
**决策**: 保留 `Agent/venv/` 用于独立运行，但建议使用后端环境

**理由**:
- Agent 可能需要独立运行，保留虚拟环境提供灵活性
- 文档中说明推荐使用后端环境，但保留独立环境作为备选

**实现方式**:
- 保留 `Agent/venv/` 目录
- 更新文档说明两种运行方式
- 在 `.gitignore` 中确保虚拟环境不被提交

### Decision 5: 导入路径策略
**决策**: 使用相对导入保持 Agent 内部模块的独立性，对外提供项目级导入路径

**理由**:
- Agent 内部模块应该保持相对导入，便于独立运行
- 如果后端需要调用 Agent，可以通过 `from Agent.sql_agent import run_agent` 的方式

**实现方式**:
- Agent 内部文件使用相对导入（`from config import config`）
- 确保 Agent 文件夹在 Python 路径中，或使用 `sys.path` 添加

## Risks / Trade-offs

### Risk 1: 导入路径错误
**风险**: 移动文件或更新导入路径可能导致导入错误

**缓解措施**:
- 仔细测试所有导入语句
- 使用 IDE 的导入检查功能
- 编写测试验证导入正确性

### Risk 2: 依赖版本冲突
**风险**: 合并依赖时可能出现版本冲突

**缓解措施**:
- 仔细检查现有依赖版本
- 选择兼容的版本范围
- 在测试环境中验证依赖兼容性

### Risk 3: 配置系统冲突
**风险**: Agent 和后端的配置系统可能不兼容

**缓解措施**:
- 使用适配器模式隔离配置系统
- 保持 Agent 配置的独立性作为备选
- 充分测试配置加载逻辑

## Migration Plan

### Phase 1: 准备阶段
1. 备份 Agent 文件夹
2. 分析依赖和配置
3. 记录环境变量需求

### Phase 2: 依赖整合
1. 合并依赖到 `backend/requirements.txt`
2. 解决版本冲突
3. 验证依赖安装

### Phase 3: 配置整合
1. 分析配置需求
2. 更新后端配置系统（如需要）
3. 创建配置适配器（如需要）

### Phase 4: 代码更新
1. 更新导入路径
2. 测试导入正确性
3. 修复任何导入错误

### Phase 5: 测试和验证
1. 安装依赖
2. 测试 Agent 独立运行
3. 测试配置加载
4. 测试核心功能

### Phase 6: 文档和清理
1. 更新文档
2. 清理不需要的文件
3. 更新 `.gitignore`

### 回滚计划
如果集成过程中出现问题：
1. 恢复备份的 Agent 文件夹
2. 恢复 `backend/requirements.txt` 的原始状态
3. 检查并恢复任何修改的配置文件

## Open Questions - 已解答

### 1. Agent 是否需要集成到后端服务中？

**答案：必须集成，作为前端 AI 助手的核心功能**

**最终目标**：
- **在前端 AI 助手页面（`/ai-assistant`）中实现 Agent 的功能**
- 前端用户通过 AI 助手界面与 Agent 交互，进行 SQL 查询和数据分析
- Agent 的响应（包括 SQL 结果、图表、可视化）需要在前端界面中展示

**理由**：
- 后端已有 `/api/v1/llm/chat` 和 `/api/v1/query` 端点，当前使用智谱 GLM API
- **默认切换为 DeepSeek API**：Agent 使用 LangGraph + MCP + DeepSeek API，作为默认 LLM 提供商
- Agent 提供更强大的 SQL 生成和可视化能力（基于 MCP 协议）
- DeepSeek 提供更好的成本效益和性能，适合作为默认选择
- 保留智谱 GLM 作为可选提供商，通过配置切换

**实现方案**：
- **方案 A（推荐）**：增强现有的 `/api/v1/query` 端点，内部使用 Agent 处理查询
  - 前端无需修改，继续调用 `/api/v1/query`
  - 后端内部将查询路由到 Agent 处理
  - Agent 的 `VisualizationResponse` 需要转换为前端期望的响应格式
  
- **方案 B（备选）**：创建新的 API 端点 `/api/v1/agent/query`，前端可选择使用
  - 前端可以选择使用新的 Agent 端点或旧的查询端点
  - 需要前端代码修改以支持新端点

- 保持 Agent 独立运行能力（用于开发和测试）
- 统一认证和租户隔离机制
- **响应格式兼容**：Agent 的 `VisualizationResponse` 需要转换为前端期望的格式

**建议实现（方案 A - 推荐）**：
```python
# backend/src/app/api/v1/endpoints/query.py
@router.post("/query", response_model=QueryResponseV3)
async def create_query(
    request: QueryRequest,
    tenant=Depends(get_current_tenant_from_request)
):
    """查询端点 - 使用 Agent 处理（默认使用 DeepSeek）"""
    from Agent.sql_agent import run_agent
    
    # 使用租户的数据库连接
    database_url = get_tenant_database_url(tenant.id)
    
    # 调用 Agent 处理查询
    viz_response = await run_agent(
        question=request.query,
        thread_id=f"{tenant.id}_{request.session_id or 'default'}"
    )
    
    # 转换 Agent 响应为前端期望的格式
    return QueryResponseV3(
        status="success",
        data={
            "answer": viz_response.answer,
            "sources": extract_sources_from_sql(viz_response.sql),
            "reasoning": f"执行了 SQL 查询：{viz_response.sql}",
            "confidence": 0.9 if viz_response.success else 0.5,
            "execution_time": 0,  # Agent 内部已记录
            "sql": viz_response.sql,
            "data": viz_response.data.dict() if viz_response.data else None,
            "chart": viz_response.chart.dict() if viz_response.chart else None,
            "chart_path": get_chart_url(viz_response) if has_chart(viz_response) else None
        }
    )
```

**响应格式转换**：
- Agent 的 `VisualizationResponse` 包含：`answer`, `sql`, `data`, `chart`
- 前端期望的格式包含：`answer`, `sources`, `reasoning`, `confidence`, `execution_time`, `sql`, `data`, `chart_path`
- 需要创建转换函数将 Agent 响应映射到前端格式

**配置更新**：
- 在后端配置系统中添加 DeepSeek 相关配置项（`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`）
- 将 DeepSeek 设置为默认 LLM 提供商
- 保留智谱 GLM 配置作为备选，可通过环境变量或配置切换

### 2. MCP 服务器的管理方式？

**答案：集成到 Docker Compose，作为容器服务**

**理由**：
- 项目已使用 Docker Compose 管理服务（frontend, backend, db, storage, vector_db）
- MCP 服务器是 Agent 的核心依赖，应该作为基础设施的一部分
- 容器化便于统一管理和部署

**实现方案**：
- 在 `docker-compose.yml` 中添加 MCP 服务器服务
- PostgreSQL MCP Server：作为 sidecar 容器运行
- ECharts MCP Server：作为独立服务运行（可选，Agent 也支持本地 PyEcharts）

**建议配置**：
```yaml
# docker-compose.yml 新增服务
services:
  mcp-postgres:
    image: node:20-alpine
    container_name: dataagent-mcp-postgres
    command: npx -y @modelcontextprotocol/server-postgres ${DATABASE_URL}
    environment:
      - DATABASE_URL=${DATABASE_URL}
    networks:
      - dataagent-network
    depends_on:
      - db

  mcp-echarts:
    # 可选：如果需要使用 MCP ECharts 服务器
    # 可以通过 npm 安装 mcp-echarts 并运行
    # 或者使用 Agent 的本地 PyEcharts 实现
```

**替代方案**：
- 如果 MCP 服务器启动复杂，可以保持 Agent 独立运行模式
- Agent 通过环境变量配置 MCP 服务器地址（本地或远程）

### 3. 图表生成服务的部署方式？

**答案：统一图表服务，创建共享模块**

**理由**：
- Agent 已有完整的图表生成功能（PyEcharts + MCP ECharts）
- 后端和前端未来可能也需要图表功能
- 统一服务可以避免重复代码和维护成本

**实现方案**：
- 将 `Agent/chart_service.py` 提取为共享模块
- 创建 `backend/src/app/services/chart_service.py`（或 `shared/chart_service.py`）
- Agent 和后端都可以使用该服务
- 支持多种图表类型：柱状图、折线图、饼图、散点图等

**建议结构**：
```
backend/src/app/services/
├── chart_service.py          # 统一图表生成服务
└── ...

Agent/
├── chart_service.py          # 保留作为适配器，调用共享服务
└── ...
```

**图表存储**：
- 生成的图表保存到本地文件系统（默认 `./charts` 目录）
- 返回图表文件路径或 Base64 编码的图片数据
- 支持 HTML 格式（PyEcharts 简化版）和 PNG 格式（需要 selenium）
- 图表文件可以通过后端 API 提供静态文件服务，或直接返回给前端

**总结**：
1. **Agent 集成**：部分集成，作为可选高级功能，通过新 API 端点暴露
2. **MCP 服务器**：集成到 Docker Compose，作为基础设施服务
3. **图表服务**：统一为共享模块，供 Agent 和后端共同使用

