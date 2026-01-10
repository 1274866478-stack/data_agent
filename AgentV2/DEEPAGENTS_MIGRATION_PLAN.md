# AgentV2 - LangChain DeepAgents 升级方案

## 概述

将现有 Agent 模块从 LangGraph 迁移到 LangChain DeepAgents 框架，实现 SOTA 级别的智能数据分析能力。

### 用户选择
- **迁移方式**: 完整迁移 DeepAgents
- **MCP 策略**: 保留现有 MCP 协议（PostgreSQL + ECharts）
- **部署方式**: 集成到 FastAPI 后端
- **目标**: 升级到 SOTA 级别，引入 DeepAgents 的全部核心能力

---

## 架构设计

### 新目录结构

```
AgentV2/
├── core/                        # 核心 Agent 实现
│   ├── agent_factory.py         # DeepAgents 工厂 ⭐
│   ├── base_agent.py            # 基础 Agent 类
│   ├── state_manager.py         # 状态管理
│   └── memory.py                # 记忆系统
│
├── middleware/                  # 中间件
│   ├── sql_security.py          # SQL 安全校验
│   ├── data_transformer.py      # 数据转换
│   ├── chart_generator.py       # 图表生成
│   ├── tenant_isolation.py      # 租户隔离 ⭐
│   └── xai_logger.py            # XAI 可解释性日志 ⭐
│
├── tools/                       # 工具集
│   ├── mcp_tools.py             # MCP 工具包装 ⭐
│   ├── sql_tools.py             # SQL 查询工具
│   ├── file_tools.py            # 文件分析工具
│   └── chart_tools.py           # 图表工具
│
├── subagents/                   # 子代理 ⭐
│   ├── sql_agent.py             # SQL 专家子代理
│   ├── file_agent.py            # 文件分析子代理
│   ├── chart_agent.py           # 图表专家子代理
│   └── research_agent.py        # 研究子代理
│
├── config/                      # 配置
│   ├── agent_config.py          # Agent 配置
│   ├── prompts.py               # 系统提示词
│   └── database_specs.py        # 数据库规范
│
├── models/                      # 数据模型
│   ├── requests.py              # 请求模型
│   ├── responses.py             # 响应模型
│   └── internal.py              # 内部模型
│
└── tests/                       # 测试
    ├── unit/                    # 单元测试
    ├── integration/             # 集成测试
    └── e2e/                     # 端到端测试
```

### 核心模块关系

```
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                             │
│  /api/v2/query - 新版查询端点                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AgentFactory (工厂模式)                          │
│  - create_agent() - 创建 DeepAgents 实例                     │
│  - get_or_create_agent() - 单例缓存                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  DeepAgents 核心层                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Middleware Pipeline (中间件管道)                      │   │
│  │  1. TenantIsolationMiddleware  (租户隔离)              │   │
│  │  2. TodoListMiddleware        (任务规划)               │   │
│  │  3. FilesystemMiddleware      (文件系统)               │   │
│  │  4. SubAgentMiddleware        (子代理)                 │   │
│  │  5. SQLSecurityMiddleware     (SQL安全)                │   │
│  │  6. XAILoggerMiddleware       (可解释性)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                    │
│  ┌─────────────────────────┼────────────────────────────┐    │
│  │                         │                            │    │
│  ▼                         ▼                            ▼    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ SQL Agent    │  │ File Agent   │  │ Chart Agent  │       │
│  │ 子代理        │  │ 子代理        │  │ 子代理        │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tools (工具集)                                        │   │
│  │  - MCP PostgreSQL Tools (保留)                        │   │
│  │  - MCP ECharts Tools (保留)                           │   │
│  │  - Custom Analysis Tools                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 分阶段实施计划

### Phase 0: 准备阶段 (1-2天)

**任务**:
- [ ] 创建 AgentV2 目录结构
- [ ] 安装 DeepAgents 依赖 (`pip install deepagents langgraph>=0.2.50`)
- [ ] 配置环境变量（复制 Agent/.env）
- [ ] 备份现有 Agent 代码
- [ ] 创建 Git 分支 `feature/deepagents-migration`

**关键文件**:
- `AgentV2/requirements.txt`
- `AgentV2/.env`

**验证**: 依赖安装成功，环境配置正确

---

### Phase 1: DeepAgents 基础集成 (3-5天)

**目标**: 用 DeepAgents 替换现有 LangGraph 架构

**核心文件**:

#### `AgentV2/core/agent_factory.py` ⭐
```python
from deepagents import create_deep_agent
from deepagents.middleware import (
    TodoListMiddleware,
    FilesystemMiddleware,
    SubAgentMiddleware
)

class AgentFactory:
    """DeepAgents 工厂类"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._cached_agent = None

    def create_agent(self, tenant_id: str, database_url: str, tools: list):
        """创建 Data Agent V2 实例"""
        middleware = self._build_middleware(tenant_id)

        agent = create_deep_agent(
            model=self.config.model,
            tools=tools,
            middleware=middleware
        )
        return agent

    def _build_middleware(self, tenant_id: str):
        """构建中间件列表"""
        return [
            TenantIsolationMiddleware(tenant_id),
            TodoListMiddleware(),
            FilesystemMiddleware(),
            SQLSecurityMiddleware(),
            XAILoggerMiddleware()
        ]
```

#### `AgentV2/tools/mcp_tools.py` ⭐
```python
"""MCP 工具包装层 - 保留现有 MCP 集成"""
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools(database_url: str):
    """获取 MCP 工具"""
    client = MultiServerMCPClient({
        "postgres": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-postgres", database_url]
        },
        "echarts": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-echarts"]
        }
    })
    return await client.get_tools()
```

**迁移映射**:
| 现有代码 | 新位置 | 迁移方式 |
|---------|--------|---------|
| `Agent/sql_agent.py` | `AgentV2/core/base_agent.py` | 重写 |
| `Agent/config.py` | `AgentV2/config/agent_config.py` | 扩展 |

**验证**: 基础查询功能正常

---

### Phase 2: 中间件增强 (5-7天)

**目标**: 集成现有安全和服务逻辑到中间件

**关键文件**:

#### `AgentV2/middleware/tenant_isolation.py` ⭐
```python
class TenantIsolationMiddleware(Middleware):
    """多租户隔离中间件"""

    def __init__(self, tenant_id: str):
        super().__init__()
        self.tenant_id = tenant_id

    def pre_process(self, agent_input: Dict) -> Dict:
        agent_input["tenant_id"] = self.tenant_id
        return agent_input
```

#### `AgentV2/middleware/sql_security.py`
```python
class SQLSecurityMiddleware(Middleware):
    """SQL 安全校验中间件 - 从 sql_validator.py 迁移"""

    def __init__(self):
        super().__init__()
        self.dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', ...]

    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """验证 SQL 安全性"""
        # 实现验证逻辑
        pass
```

#### `AgentV2/middleware/xai_logger.py` ⭐
```python
class XAILoggerMiddleware(Middleware):
    """XAI 可解释性日志中间件"""

    def post_process(self, agent_output: Dict) -> Dict:
        reasoning_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "steps": self._extract_reasoning_steps(agent_output),
            "tools_used": self._extract_tool_calls(agent_output),
            "decisions": self._extract_decision_points(agent_output)
        }
        agent_output["xai_log"] = reasoning_log
        return agent_output
```

**验证**: 安全校验正常，日志记录完整

---

### Phase 3: 子代理架构 (7-10天)

**目标**: 实现专业化子代理

**关键文件**:

#### `AgentV2/subagents/__init__.py` ⭐
```python
from deepagents.middleware.subagents import SubAgentMiddleware

def create_data_agent_subagents():
    """创建数据分析子代理"""
    return SubAgentMiddleware(
        default_model="deepseek-chat",
        subagents=[
            create_sql_subagent(),
            create_file_subagent(),
            create_chart_subagent()
        ]
    )
```

#### `AgentV2/subagents/sql_agent.py`
```python
def create_sql_subagent() -> Dict:
    """SQL 专家子代理"""
    return {
        "name": "sql_expert",
        "description": "SQL 查询和优化专家",
        "system_prompt": """你是 SQL 专家...
- 理解复杂查询需求
- 生成高效 SQL 语句
- 优化查询性能
- 诊断 SQL 错误""",
        "tools": [list_tables, get_schema, execute_sql, optimize_query],
        "model": "deepseek-chat"
    }
```

**子代理设计**:
```
Main Agent (协调者)
    ├── SQL Agent (查询专家)
    ├── File Agent (文件分析)
    ├── Chart Agent (可视化)
    └── Research Agent (深度研究)
```

**验证**: 子代理正确委派任务

---

### Phase 4: 高级特性 (10-14天)

**目标**: 实现 SOTA 级别功能

**关键实现**:

#### 持久化记忆系统
```python
# AgentV2/core/memory.py
from langgraph.store.postgres import AsyncPostgresStore
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

def create_persistent_memory_backend(connection_string: str):
    """创建持久化记忆后端"""
    store = AsyncPostgresStore(connection_string)
    return lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/memories/query_history/": StoreBackend(rt),
            "/memories/user_preferences/": StoreBackend(rt),
            "/memories/chart_templates/": StoreBackend(rt),
        }
    )
```

#### 多租户上下文隔离
- 租户级记忆隔离
- 查询历史分离
- 安全策略隔离

**验证**: 记忆持久化正常，租户隔离有效

---

### Phase 5: 优化与部署 (14-16天)

**目标**: 性能优化和生产部署

**关键文件**:

#### `backend/src/app/api/v1/endpoints/query_v2.py` ⭐
```python
from AgentV2.core.agent_factory import AgentFactory

@router.post("/api/v2/query")
async def create_query_v2(
    request: QueryRequestV2,
    tenant=Depends(get_current_tenant_from_request),
    agent_factory: AgentFactory = Depends(get_agent_factory)
):
    """Data Agent V2 查询端点"""
    # 获取数据源连接
    database_url = await get_database_url(request.connection_id, tenant.id)

    # 获取或创建 Agent
    agent = await agent_factory.get_or_create_agent(
        tenant_id=tenant.id,
        database_url=database_url
    )

    # 执行查询
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=request.query)]},
        config={"configurable": {"thread_id": f"{tenant.id}_{request.session_id}"}}
    )

    return QueryResponseV2(
        answer=result["messages"][-1].content,
        processing_steps=result.get("xai_log", {}).get("steps", []),
        todos=result.get("todos", []),
        subagent_calls=result.get("subagent_calls", [])
    )
```

**优化任务**:
- 连接池优化
- 查询缓存
- 并发处理
- 监控和日志

**验证**: 性能达标，部署成功

---

## 代码迁移映射表

### 核心模块

| 现有模块 | 新位置 | 迁移策略 | 复杂度 |
|---------|--------|---------|--------|
| `Agent/sql_agent.py` | `AgentV2/core/base_agent.py` | 重写 | ⭐⭐⭐⭐⭐ |
| `Agent/config.py` | `AgentV2/config/agent_config.py` | 扩展 | ⭐⭐ |
| `Agent/models.py` | `AgentV2/models/` | 保留 | ⭐ |
| `Agent/data_transformer.py` | `AgentV2/middleware/data_transformer.py` | 重构 | ⭐⭐⭐ |
| `Agent/prompt_generator.py` | `AgentV2/config/prompts.py` | 保留扩展 | ⭐⭐ |
| `Agent/sql_validator.py` | `AgentV2/middleware/sql_security.py` | 迁移 | ⭐⭐⭐ |
| `Agent/chart_service.py` | `AgentV2/middleware/chart_generator.py` | 迁移 | ⭐⭐⭐ |

### 后端集成

| 现有端点 | 新端点 | 变更说明 |
|---------|--------|---------|
| `/api/v1/query` | `/api/v2/query` | 使用 DeepAgents |
| `agent_service.py` | `agent_service_v2.py` | 使用 AgentFactory |

---

## 风险评估与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| DeepAgents API 不稳定 | 🔴 高 | Phase 1 小规模验证 + 保留 V1 回退 |
| 性能下降 | 🟡 中 | 基准测试 + 连接池优化 |
| 中间件冲突 | 🟡 中 | 单元测试 + 集成验证 |
| 依赖兼容性 | 🟢 低 | 虚拟环境隔离 |

---

## 测试策略

### 单元测试
- `tests/unit/test_agent_factory.py` - AgentFactory 测试
- `tests/unit/test_middleware.py` - 中间件测试
- `tests/unit/test_tools.py` - 工具测试

### 集成测试
- `tests/integration/test_query_flow.py` - 查询流程测试
- `tests/integration/test_subagent_flow.py` - 子代理测试

### 性能测试
- 简单查询: <3s
- 复杂查询: <12s
- 并发处理: >15 req/s

### 回归测试
- V1 vs V2 输出一致性验证

---

## 验证方案

### 功能验证
| 功能 | 验证方法 | 预期结果 |
|------|---------|---------|
| SQL 查询 | 单元测试 | 与 V1 一致 |
| 文件分析 | 集成测试 | 正确解析 |
| 图表生成 | 视觉验证 | ECharts 正确 |
| 多轮对话 | 回归测试 | 上下文保持 |
| 子代理委派 | E2E 测试 | 正确委派 |

### 性能验证
| 指标 | V1 基准 | V2 目标 |
|------|---------|---------|
| 简单查询 | <3s | <3s |
| 复杂查询 | <15s | <12s |
| 并发处理 | 10 req/s | 15 req/s |

---

## 关键文件清单 ⭐

实施此方案的**最关键文件**：

1. **`AgentV2/core/agent_factory.py`** - DeepAgents 工厂类
2. **`AgentV2/tools/mcp_tools.py`** - MCP 工具包装
3. **`AgentV2/middleware/tenant_isolation.py`** - 租户隔离
4. **`AgentV2/middleware/xai_logger.py`** - 可解释性日志
5. **`AgentV2/subagents/__init__.py`** - 子代理配置
6. **`backend/src/app/api/v1/endpoints/query_v2.py`** - 新版 API

---

## 参考资料

- [DeepAgents 官方文档](https://docs.langchain.com/oss/python/deepagents)
- [LangChain GitHub](https://github.com/langchain-ai/deepagents)
- [现有 Agent 文档](../Agent/README.md)

---

## 下一步行动

1. ✅ 评审本方案，确认技术方向
2. 创建 `feature/deepagents-migration` 分支
3. 开始 Phase 0: 准备阶段
4. 按分阶段计划逐步实施

---

**创建时间**: 2025-01-10
**版本**: v1.0
**状态**: 待审批
