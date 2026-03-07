# AgentV2 - SOTA Multi-Agent SQL Intelligence System

**模块**: 高级多代理SQL智能系统
**版本**: V2.0
**技术栈**: LangGraph + DeepSeek + Qdrant + Cube.js + MCP
**最后更新**: 2026-03-07

---

## 模块概述

AgentV2 是基于 **Swarm Architecture** 的高级多代理系统，通过中间件管道实现智能 SQL 查询、语义层集成和企业级知识管理。

---

## 核心架构

### Swarm Graph (`graphs/swarm_graph.py`)
```python
# 多代理编排系统
- 动态代理选择基于查询复杂度
- 跨代理交互的状态管理
- 支持代理并行和串行执行
```

### 中间件管道 (`middleware/`)

| 中间件 | 功能 |
|--------|------|
| `loop_detection.py` | 检测并打破无限循环 |
| `time_aggregation.py` | 智能时态 SQL 生成（自动处理日期截断、周月聚合） |
| `tenant_isolation.py` | 强制多租户数据隔离 |
| `sql_security.py` | SQL 注入防护 |
| `error_tracker.py` | 错误分类与恢复 |
| `chart_guidance.py` | 图表类型推荐 |
| `knowledge_middleware.py` | 知识库集成 |
| `semantic_priority.py` | 语义层优先级 |
| `xai_logger.py` | 可解释性日志 |
| `table_cache_middleware.py` | 表结构缓存 |

### 子代理系统 (`subagents/`)

```python
# 专门化的子代理
planner_agent.py     # 查询规划和任务分解
generator_agent.py   # SQL 生成
critic_agent.py      # 结果验证和质量评估
repair_agent.py      # 错误修复
router_agent.py      # 路由和代理选择
```

### 节点系统 (`nodes/`)

```python
planning_node.py         # 查询理解与规划
clarification_node.py    # 用户澄清请求
analysis_node.py         # 数据分析执行
reflection_node.py       # 结果反思与改进
learning_node.py         # 从错误中学习
```

---

## SOTA 功能

### 🧠 知识增强
- **Qdrant 向量存储**: 业务术语和表关系的语义检索
- **业务词汇表** (`context/business_glossary.py`): 领域知识管理
- **实体链接** (`entity_linking.py`): 智能实体识别和关联

### 📊 语义层集成
- **Cube.js 集成**: 预聚合指标和语义查询
- **语义层工具** (`tools/semantic_layer_tools.py`): Cube.js API 封装
- **Join 推理** (`cube_joins.py`): 自动表关联推断

### 🔧 工具系统 (`tools/`)

```python
database_tools.py         # 数据库查询工具
chart_tools.py            # 图表生成工具
mcp_tools.py              # MCP 协议集成
semantic_layer_tools.py   # Cube.js 语义层
schema_metadata.py        # Schema 元数据管理
general_tools.py          # 通用工具集
python_sandbox_tools.py   # Python 沙箱执行
```

---

## 测试

```bash
# 单元测试
pytest AgentV2/tests/unit/ -v

# E2E 测试
pytest AgentV2/tests/e2e_complete_test.py -v

# 性能基准测试
pytest AgentV2/tests/performance_benchmark.py -v

# 特定测试
pytest AgentV2/tests/test_time_aggregation_sql.py -v
pytest AgentV2/tests/unit/test_tenant_isolation.py -v

# SQL 清理测试
pytest AgentV2/tests/unit/test_sql_cleaning.py -v
```

---

## 配置

### 环境变量
```env
# SOTA 功能开关
USE_SOTA_AGENT=true
ENABLE_SEMANTIC_LAYER=true
ENABLE_FEW_SHOT_RAG=true
ENABLE_SELF_HEALING=true

# Qdrant 配置
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Cube.js 配置
CUBE_API_URL=http://cube:4000
CUBEJS_API_SECRET=your_secret
```

---

## 与 Agent/ 的区别

| 特性 | Agent/ | AgentV2/ |
|------|--------|----------|
| 架构 | 单一 Agent | Swarm 多代理 |
| 中间件 | 无 | 14 个中间件组件 |
| 知识库 | 无 | Qdrant + 业务词汇表 |
| 语义层 | 无 | Cube.js 集成 |
| 错误恢复 | 基础 | 自愈 + 学习 |
| 时间聚合 | 手动 | 智能自动 |
| 租户隔离 | 手动 | 强制中间件 |

---

## 使用示例

```python
# 在后端使用 AgentV2
from AgentV2.sql_agent import SQLAgent as SQLAgentV2

agent = SQLAgentV2(
    tenant_id="tenant_123",
    use_sota_features=True
)

result = await agent.query("显示最近三个月的销售趋势")
# 自动应用 time_aggregation 中间件处理时态
# 自动使用 semantic_layer 获取预聚合数据
```

---

**🚀 SOTA 提示**: AgentV2 是生产就绪的企业级系统，优先使用它而不是 Agent/ 用于新功能开发。
