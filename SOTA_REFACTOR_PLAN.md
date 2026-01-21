# SOTA ChatBI 重构计划

## 项目目标

将 Data Agent V4 从单一 Text-to-SQL Agent 升级为 SOTA 级别的 **Cognitive Decision Engine（认知决策引擎）**，实现"零幻觉"的企业级 BI 平台。

---

## 核心架构变更

### 当前架构 → 目标架构

| 组件 | 当前架构 | SOTA 架构 |
|------|----------|-----------|
| **SQL 生成** | LLM 直接生成 SQL | LLM 生成 DSL → 语义层编译 |
| **验证机制** | SQL 质量检查 | 多智能体博弈（Planner → Generator → Critic） |
| **错误处理** | 简单重试 | 自愈机制（Repair Agent） |
| **学习方式** | 静态 Prompt | 动态少样本 RAG |
| **查询路由** | 简单条件判断 | 认知路由 + 主动消歧 |

---

## 分阶段实施计划

### Phase 1: 语义层集成（2-3周）

#### 目标
部署 Cube.js 语义层，建立 Single Source of Truth

#### 技术选型
- **语义层**: Cube.js (Docker 部署)
- **向量数据库**: Qdrant (迁移自 ChromaDB)

#### 交付物

**1. Cube.js 部署**
```yaml
# docker-compose.cube.yml 新增
services:
  cube:
    image: cubejs/cube:latest
    ports:
      - "4000:4000"
    environment:
      - CUBEJS_DB_TYPE=postgres
      - CUBEJS_DB_HOST=dataagent-postgres # 使用容器名
      - CUBEJS_API_SECRET=${CUBEJS_API_SECRET} # 使用环境变量
    volumes:
      - ./cube_schema:/cube/schema
    networks:
      - dataagent-network

networks:
  dataagent-network:
    external: true
```

**2. 核心文件创建**
```
backend/src/app/services/semantic_layer/
├── __init__.py
├── cube_service.py          # Cube API 封装
├── cube_definitions.py      # Cube 定义存储
├── semantic_cache.py        # Redis 缓存
└── models.py               # Cube, Measure, Dimension 模型
```

**3. Cube 定义示例**
```yaml
# cube_schema/Orders.yaml
cube: Orders
measures:
  - name: total_revenue
    sql: ${amount}
    type: sum
  - name: order_count
    sql: ${id}
    type: count

dimensions:
  - name: created_at
    sql: ${created_at}
    type: time
  - name: status
    sql: ${status}
    type: string
```

**4. 数据库迁移**
```sql
-- 新增语义层相关表
-- ⚠️ 注意：生产环境请使用 scripts/migrate_v4_to_v5.py 或 Alembic 执行，不要直接运行 SQL
-- 新增语义层相关表
CREATE TABLE IF NOT EXISTS cubes (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    cube_name VARCHAR(255) UNIQUE NOT NULL,
    cube_definition JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cube_measures (
    id SERIAL PRIMARY KEY,
    cube_id INTEGER REFERENCES cubes(id),
    measure_name VARCHAR(255) NOT NULL,
    measure_type VARCHAR(50) NOT NULL
);
```

#### 验证标准
- [ ] Cube.js 服务正常运行
- [ ] 可通过 API 执行基础查询
- [ ] 多租户 Cube 隔离生效

---

### Phase 2: 多智能体框架（2周）

#### 目标
实现 Router → Planner → Generator → Critic 编排

#### 交付物

**1. 代码重构与新 Agent 模块**
- **重构**: 将 `AgentV2/sql_agent.py` 移动至 `AgentV2/legacy/sql_agent_old.py`
- **新结构**:
```
AgentV2/subagents/
├── __init__.py
├── base_agent.py           # Agent 基类
├── router_agent.py         # 路由器：消歧检测
├── planner_agent.py        # 规划师：任务分解
├── generator_agent.py      # 生成器：DSL JSON
├── critic_agent.py         # 审查员：业务规则验证
└── agent_swarm.py          # 编排器
```

**2. 新状态图**
```python
# AgentV2/graphs/swarm_graph.py
class ChatBiState(TypedDict):
    query: str
    route_decision: Optional[RouteDecision]
    query_plan: Optional[QueryPlan]
    dsl_json: Optional[Dict]
    critic_report: Optional[CriticReport]
    final_result: Optional[QueryResult]
    error_count: int

def build_swarm_graph():
    builder = StateGraph(ChatBiState)
    builder.add_node("router", router_node)
    builder.add_node("planner", planner_node)
    builder.add_node("generator", generator_node)
    builder.add_node("critic", critic_node)
    builder.add_node("repair", repair_node)
    # ... 边连接
```

**3. 业务规则示例**
```yaml
# rules/business_rules.yaml
rules:
  - name: "dau_must_use_distinct"
    pattern: "count(user_id)"
    replacement: "count(DISTINCT user_id)"
    explanation: "DAU 必须去重计算"

  - name: "revenue_filter_valid_range"
    field: "amount"
    validation: "value >= 0"
    error_message: "金额不能为负"
```

#### 验证标准
- [ ] 多智能体工作流可正常运行
- [ ] Critic 可拦截错误 DSL
- [ ] 修复循环可自动纠正错误

---

### Phase 3: 动态少样本 RAG（2周）

#### 目标
从历史成功案例中学习，动态构建 Prompt

#### 交付物

**1. Qdrant 集成**
```python
# backend/src/app/services/qdrant_client.py
class QdrantService:
    async def store_successful_query(
        self,
        question: str,
        dsl_json: Dict,
        embedding: List[float],
        tenant_id: str
    ):
        """存储成功查询到向量库"""

    async def find_similar_queries(
        self,
        question: str,
        top_k: int = 3
    ) -> List[SuccessfulQuery]:
        """检索相似历史案例"""
```

**2. 数据模型**
```sql
-- 成功查询历史表
CREATE TABLE successful_queries (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    original_question TEXT NOT NULL,
    rewritten_question TEXT,
    dsl_json JSONB NOT NULL,
    execution_time_ms INTEGER,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    embedding VECTOR(1536),  -- pgvector
    created_at TIMESTAMP DEFAULT NOW()
);
```

**3. 动态 Prompt 构建**
```python
# few_shot_rag/prompt_builder.py
async def build_few_shot_prompt(
    question: str,
    examples: List[SuccessfulQuery]
) -> str:
    template = """
# 参考案例

{examples}

# 当前问题
{question}

请参考上述案例，为当前问题生成符合语义层规范的 DSL JSON。
"""
```

#### 验证标准
- [ ] Qdrant 服务正常运行
- [ ] 可检索相似历史案例
- [ ] 动态 Prompt 可提升生成质量

---

### Phase 4: 自愈机制（2周）

#### 目标
自动修复常见 DSL 错误

#### 交付物

**1. 错误模式库**
```yaml
# self_healing/error_patterns.yaml
patterns:
  - name: "measure_not_found"
    regex: "Measure '(\w+)' not found"
    fix_strategy: "suggest_similar_measures"

  - name: "invalid_join"
    regex: "Cannot join.*"
    fix_strategy: "use_precomputed_joins"

  - name: "missing_filter"
    regex: "Required filter missing"
    fix_strategy: "infer_from_context"
```

**2. 修复历史**
```sql
CREATE TABLE repair_history (
    id SERIAL PRIMARY KEY,
    original_dsl JSONB NOT NULL,
    error_message TEXT NOT NULL,
    repaired_dsl JSONB NOT NULL,
    repair_strategy VARCHAR(255),
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**3. 修复器实现**
```python
# self_healing/dsl_repairer.py
class DSLRepairer:
    async def repair_dsl(
        self,
        broken_dsl: Dict,
        error_message: str,
        cube_schema: CubeSchema
    ) -> RepairResult:
        """分析错误并修复 DSL"""
```

#### 验证标准
- [ ] 可自动识别常见错误模式
- [ ] 修复成功率 > 70%
- [ ] 修复历史可学习优化

---

### Phase 5: 主动消歧（1-2周）

#### 目标
检测模糊查询并生成澄清问题

#### 交付物

**0. 依赖更新**
Add to `requirements.txt`:
```text
qdrant-client>=1.7.0
dirtyjson>=1.0.8  # 用于修复 JSON
```

**1. 消歧检测器**
```python
# disambiguation/ambiguity_detector.py
class AmbiguityDetector:
    async def detect_ambiguity(
        self,
        question: str,
        context: QueryContext
    ) -> AmbiguityReport:
        """检测查询中的模糊表达"""
```

**2. 反问生成器**
```python
# disambiguation/question_generator.py
async def generate_clarifying_questions(
    ambiguity_type: AmbiguityType
) -> List[str]:
    """生成澄清问题"""
    # 示例：
    # - "您指的'最好'是按销售额还是订单量？"
    # - "需要哪个时间范围的数据？"
```

#### 验证标准
- [ ] 可检测模糊关键词（最好、最近、销售等）
- [ ] 生成的问题自然易懂
- [ ] 用户反馈可闭环学习

---

## 关键文件清单

### 需要修改的文件

| 文件路径 | 修改内容 | 优先级 |
|----------|----------|--------|
| `AgentV2/sql_agent.py` | 重构为 `AgentV2/legacy/sql_agent_legacy.py` | P0 |
| `AgentV2/graphs/swarm_graph.py` | 新建多智能体状态图 | P0 |
| `backend/src/app/services/agent_service.py` | 集成 Swarm Agent | P0 |
| `backend/src/app/api/v1/endpoints/query.py` | 新增 `/query/sota` 端点 | P0 |
| `backend/src/app/data/models.py` | 新增语义层相关模型 | P0 |
| `docker-compose.yml` | 添加 Cube.js 和 Qdrant | P0 |

### 需要新建的文件

**Phase 1 (语义层)**
- `backend/src/app/services/semantic_layer/__init__.py`
- `backend/src/app/services/semantic_layer/cube_service.py`
- `backend/src/app/services/semantic_layer/semantic_cache.py`
- `cube_schema/Orders.yaml` (示例 Cube 定义)
- `docker-compose.cube.yml`

**Phase 2 (多智能体)**
- `AgentV2/subagents/__init__.py`
- `AgentV2/subagents/base_agent.py`
- `AgentV2/subagents/router_agent.py`
- `AgentV2/subagents/planner_agent.py`
- `AgentV2/subagents/generator_agent.py`
- `AgentV2/subagents/critic_agent.py`
- `AgentV2/subagents/repair_agent.py`
- `AgentV2/graphs/swarm_graph.py`
- `rules/business_rules.yaml`

**Phase 3 (少样本 RAG)**
- `backend/src/app/services/qdrant_client.py`
- `backend/src/app/services/few_shot_rag/__init__.py`
- `backend/src/app/services/few_shot_rag/query_history_store.py`
- `backend/src/app/services/few_shot_rag/similarity_matcher.py`
- `backend/src/app/services/few_shot_rag/prompt_builder.py`

**Phase 4 (自愈)**
- `backend/src/app/services/self_healing/__init__.py`
- `backend/src/app/services/self_healing/error_pattern_matcher.py`
- `backend/src/app/services/self_healing/dsl_repairer.py`
- `backend/src/app/services/self_healing/repair_memory.py`
- `self_healing/error_patterns.yaml`

**Phase 5 (消歧)**
- `backend/src/app/services/disambiguation/__init__.py`
- `backend/src/app/services/disambiguation/ambiguity_detector.py`
- `backend/src/app/services/disambiguation/question_generator.py`

---

## 向后兼容策略

### API 兼容层
```python
# backend/src/app/api/v1/endpoints/query.py
@router.post("/query")  # 保持原端点
async def create_query_legacy(request: QueryRequest):
    if settings.use_sota_agent:
        adapter = LegacyToSOTAAdapter()
        sota_request = await adapter.adapt_request(request)
        sota_response = await run_swarm_agent(sota_request)
        return await adapter.adapt_response(sota_response)
    else:
        return await legacy_query_handler(request)

@router.post("/query/sota")  # 新端点
async def create_query_sota(request: SOTAQueryRequest):
    return await run_swarm_agent(request)
```

### 配置开关
```python
# backend/src/app/core/config.py
class Settings:
    use_sota_agent: bool = Field(
        default=False,
        description="启用 SOTA 多智能体架构"
    )
    enable_few_shot: bool = True
    enable_self_healing: bool = True
    enable_disambiguation: bool = True
```

---

## 数据库迁移脚本

```sql
-- === Phase 1: 语义层 ===
CREATE TABLE cubes (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    cube_name VARCHAR(255) NOT NULL,
    cube_definition JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, cube_name)
);
-- 建议创建 scripts/migrate_v4_to_v5.py 使用 psycopg2 执行上述变更，并处理异常。

-- === Phase 3: 少样本 RAG ===
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE successful_queries (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    original_question TEXT NOT NULL,
    rewritten_question TEXT,
    dsl_json JSONB NOT NULL,
    execution_time_ms INTEGER,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_successful_queries_embedding
ON successful_queries USING ivfflat (embedding vector_cosine_ops);

-- === Phase 4: 自愈机制 ===
CREATE TABLE repair_history (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    original_dsl JSONB NOT NULL,
    error_message TEXT NOT NULL,
    repaired_dsl JSONB NOT NULL,
    repair_strategy VARCHAR(255),
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 测试策略

### 单元测试目标
- 代码覆盖率 ≥ 80%
- 每个 Agent 有独立测试
- 语义层 API 有完整 Mock 测试

### 集成测试场景
1. **完整查询流程**: 用户问题 → Router → Few-Shot → Swarm → 结果
2. **自愈测试**: 故意生成错误 DSL → 验证自动修复
3. **消歧测试**: 模糊查询 → 生成反问 → 用户回答 → 重新查询

### 性能指标
| 指标 | 当前 | 目标 |
|------|------|------|
| 查询响应时间 (P95) | ~10s | < 5s |
| 语义层查询 | N/A | < 2s |
| 向量检索 | N/A | < 500ms |
| 查询准确率 | ~60% | > 85% |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Cube.js 部署复杂 | 提前在 Docker 环境验证 |
| 多智能体调试困难 | 添加详细日志和 LangSmith 追踪 |
| Qdrant 迁移成本 | 使用 qdrant-client 异步迁移脚本 |
| API 破坏性变更 | 使用适配器模式保持兼容 |
| LLM 成本增加 | 实施查询缓存和语义层缓存 |

---

## 实施顺序建议

1. **Week 1-2**: Phase 1 - 部署 Cube.js，定义第一个 Cube
2. **Week 3-4**: Phase 2 - 实现 Router + Planner + Generator
3. **Week 5-6**: Phase 2 - 实现 Critic + Repair 循环
4. **Week 7-8**: Phase 3 - Qdrant 集成 + 少样本检索
5. **Week 9-10**: Phase 4 - 自愈机制实现
6. **Week 11-12**: Phase 5 - 主动消歧功能
7. **Week 13-14**: 全面测试 + 性能优化
8. **Week 15-16**: 文档完善 + 上线准备

---

## 验证检查清单

### Phase 1 验证
- [ ] Cube.js API 可正常调用
- [ ] 可执行基础语义层查询
- [ ] 多租户 Cube 隔离生效

### Phase 2 验证
- [ ] 多智能体工作流可运行
- [ ] Critic 可拦截错误 DSL
- [ ] 修复循环可自动纠正

### Phase 3 验证
- [ ] Qdrant 可存储/检索向量
- [ ] 相似案例检索有效
- [ ] 动态 Prompt 提升质量

### Phase 4 验证
- [ ] 常见错误可自动修复
- [ ] 修复成功率 > 70%
- [ ] 修复历史可学习

### Phase 5 验证
- [ ] 模糊查询可检测
- [ ] 反问问题自然
- [ ] 用户反馈可闭环

---

## 预期收益

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 查询准确率 | 60% | 85%+ | +42% |
| 平均响应时间 | 10s | 5s | -50% |
| 自愈成功率 | 0% | 70%+ | +70% |
| 用户满意度 | 3.5/5 | 4.5/5+ | +29% |
| 维护成本 | 高 | 低 | -90% |
