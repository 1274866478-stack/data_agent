# 语义层增强功能 - 使用指南

## 概述

本模块实现了基于向量检索和语义增强的智能数据处理功能，作为 Data Agent V4 项目与参考逻辑对比后的优化实现。

## 新增功能模块

### 1. 向量检索 Entity Linking (`entity_linking.py`)

**功能**: 基于向量相似度的智能实体匹配

**解决的问题**:
- "P40" → "Huawei P40 Pro" 模糊匹配
- "魔都" → "上海" 别名映射
- "iPhone" → "Apple iPhone 15 Pro" 层级实体匹配

**核心类**:
```python
from AgentV2.entity_linking import EntityLinkingService

service = EntityLinkingService()
results = service.link("P40", top_k=3)
```

**存储后端支持**:
- `InMemoryEntityStore`: 内存存储（测试用）
- `ChromaDBEntityStore`: ChromaDB 持久化存储（生产推荐）

**嵌入服务支持**:
- `SentenceTransformerEmbedding`: 本地多语言模型
- 可扩展 OpenAI/智谱/DeepSeek 等云端嵌入

### 2. Cube Joins 解析器 (`cube_joins.py`)

**功能**: 解析和验证 Cube 之间的 Join 关系

**YAML 配置格式**:
```yaml
joins:
  - name: Customers
    sql: ${Orders}.customer_id = ${Customers}.id
    relationship: many_to_one
    join_type: LEFT
    metadata:
      description: "订单所属的客户"
```

**核心类**:
```python
from AgentV2.cube_joins import CubeJoinsParser, JoinSQLGenerator

parser = CubeJoinsParser()
generator = JoinSQLGenerator(parser)

# 获取 Join 路径
path = parser.get_join_path("Orders", "Customers")

# 生成 JOIN SQL
join_clause, alias_map = generator.generate_join_clause(
    primary_cube="Orders",
    required_cubes=["Customers"]
)
```

### 3. Schema Pruning 向量化 (`schema_pruning.py`)

**功能**: 基于查询内容智能剪枝 Schema，减少 Token 消耗

**优势**:
- 减少 LLM 上下文大小
- 提高响应质量
- 支持大规模 Schema

**使用示例**:
```python
from AgentV2.schema_pruning import SchemaPruningService

service = SchemaPruningService()
result = service.prune("订单总收入是多少")

print(f"削减率: {result.reduction_rate:.1%}")
print(f"选中的度量: {[m.name for m in result.selected_measures]}")
```

### 4. 业务术语表外部化 (`business_glossary.json`)

**功能**: 将硬编码的术语表迁移到 JSON 配置文件

**配置文件位置**: `AgentV2/business_glossary.json`

**支持的术语类型**:
- `city_alias`: 城市别名
- `business_metric`: 业务指标缩写
- `status_value`: 状态值映射
- `time_expression`: 时间表达式
- `analytics_term`: 分析术语
- `product`: 产品实体

**热更新支持**:
```python
from AgentV2.context.business_glossary import BusinessGlossary

glossary = BusinessGlossary(
    custom_glossary_path="path/to/glossary.json",
    enable_hot_reload=True
)

# 自动检测文件变更并重新加载
glossary.reload_if_needed()
```

### 5. 统一增强管道 (`semantic_enhancement_pipeline.py`)

**功能**: 集成所有语义层增强功能的统一入口

**使用示例**:
```python
from AgentV2.semantic_enhancement_pipeline import SemanticEnhancementPipeline

pipeline = SemanticEnhancementPipeline(
    enable_entity_linking=True,
    enable_glossary=True,
    enable_schema_pruning=True,
    enable_joins=True
)

# 处理 Agent 输入
agent_input = {
    "query": "魔都的 P40 手机销售额是多少",
    "tenant_id": "xxx"
}
enhanced = pipeline.process_agent_input(agent_input)

# 增强系统提示词
system_prompt = pipeline.enhance_system_prompt(
    base_prompt="你是一个数据分析助手...",
    query="魔都的 P40 手机销售额是多少"
)
```

## 与参考逻辑的对比

| 功能 | Data Agent V4 (本次实现) | 参考逻辑 | 状态 |
|------|-------------------------|----------|------|
| Entity Linking | ChromaDB 向量检索 | 向量检索 | ✅ 已实现 |
| Business Glossary | JSON 外部化 + 热更新 | JSON 配置 | ✅ 已实现 |
| Joins 定义 | YAML + 解析器 + SQL生成 | YAML 配置 | ✅ 已实现 |
| Schema Pruning | 向量相似度剪枝 | 向量检索剪枝 | ✅ 已实现 |

## 安装依赖

```bash
# 核心依赖（已有）
pip install pyyaml numpy

# 向量检索依赖
pip install sentence-transformers  # 本地嵌入模型
pip install chromadb               # 向量数据库（可选，生产环境推荐）

# 或者使用云端嵌入 API
# pip install zhipuai  # 智谱 AI
# pip install openai   # OpenAI
```

## 测试

```bash
# 测试 Entity Linking
cd AgentV2
python entity_linking.py

# 测试 Cube Joins
python cube_joins.py

# 测试 Schema Pruning
python schema_pruning.py

# 测试完整管道
python semantic_enhancement_pipeline.py
```

## 配置文件

### 业务术语表配置

编辑 `AgentV2/business_glossary.json` 添加自定义术语：

```json
{
  "entries": [
    {
      "id": "unique_id",
      "term": "标准术语",
      "aliases": ["别名1", "别名2"],
      "mapping_type": "city_alias|business_metric|...",
      "target_value": "目标值",
      "metadata": {
        "description": "描述"
      }
    }
  ]
}
```

### Cube Joins 配置

编辑 `cube_schema/*.yaml` 添加 Join 定义：

```yaml
joins:
  - name: TargetCube
    sql: ${SourceCube}.column = ${TargetCube}.column
    relationship: many_to_one
    join_type: LEFT
```

## API 集成示例

### FastAPI 端点集成

```python
from fastapi import APIRouter, Depends
from AgentV2.semantic_enhancement_pipeline import create_default_pipeline

router = APIRouter()
pipeline = create_default_pipeline()

@router.post("/api/v1/query")
async def natural_query(request: QueryRequest):
    # 应用语义层增强
    enhanced_input = pipeline.process_agent_input({
        "query": request.query,
        "tenant_id": request.tenant_id
    })

    # 使用增强后的输入调用 Agent
    result = await agent.run(enhanced_input)

    return result
```

## 性能优化建议

1. **向量嵌入缓存**: 使用 `lru_cache` 缓存常用查询的嵌入向量
2. **ChromaDB 持久化**: 生产环境使用 ChromaDB 而非内存存储
3. **Schema 预计算**: 在启动时预计算所有元素的嵌入向量
4. **热更新节流**: 业务术语表热更新添加时间间隔限制

## 故障排查

### Entity Linking 无结果
- 检查嵌入服务是否正常工作
- 调整相似度阈值 `semantic_threshold`

### Schema 剪枝效果不佳
- 检查查询文本是否包含相关关键词
- 调整相似度阈值 `similarity_threshold`
- 增加 `max_measures` 和 `max_dimensions`

### Joins 路径未找到
- 检查 YAML 文件中的 joins 配置
- 确认关系类型 `relationship` 定义正确
- 使用 `validate_joins()` 检查配置错误

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 2.0.0 | 2025-01-28 | 实现向量检索 Entity Linking、Joins 解析、Schema Pruning、术语表外部化 |
