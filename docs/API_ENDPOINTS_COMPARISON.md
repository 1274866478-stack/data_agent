# API 端点对比文档

## 概述

本文档详细说明了 Data Agent 系统中两个不同的 API 端点及其用途差异。

---

## 端点对比表

| 特性 | `/api/v1/llm/chat/completions` | `/api/v1/query` |
|------|------------------------------|-----------------|
| **主要用途** | LLM对话、SQL预览 | 执行查询、返回结果 |
| **是否执行SQL** | ❌ 否 | ✅ 是 |
| **connection_id** | 不需要 | **必需** |
| **返回内容** | AI生成的文本 | 实际查询结果+图表 |
| **响应速度** | 快（无DB查询） | 慢（包含DB查询） |
| **适用场景** | 快速对话、SQL预览 | 端到端数据分析 |
| **风险等级** | 低（只读LLM） | 中（执行SQL） |

---

## 1. `/api/v1/llm/chat/completions` - LLM对话端点

### 设计目的
提供标准化的LLM对话接口，兼容OpenAI格式。主要用于：
- 快速自然语言对话
- SQL查询预览
- Schema查询
- 不需要实际数据库查询的场景

### 请求格式
```json
POST /api/v1/llm/chat/completions
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "2024年总销售额是多少？"}
  ],
  "stream": false,
  "data_source_ids": null
}
```

### 响应格式
```json
{
  "content": "让我帮你查询2024年的总销售额...\n\n```sql\nSELECT SUM(amount) FROM sales WHERE year = 2024\n```\n\n这个查询将返回2024年的总销售额数据。",
  "usage": {
    "total_tokens": 150
  }
}
```

### 特点
- ✅ 响应速度快（不执行SQL）
- ✅ 无需数据库连接
- ✅ 安全性高（只读LLM）
- ❌ 不返回实际查询结果
- ❌ 无法生成基于真实数据的图表

### 适用场景
- 快速对话交流
- SQL语句预览和验证
- Schema信息查询
- 开发调试阶段

---

## 2. `/api/v1/query` - 查询执行端点

### 设计目的
端到端的自然语言查询，包含SQL执行和结果返回。主要用于：
- 执行实际的数据库查询
- 获取真实的查询结果数据
- 生成基于实际数据的可视化图表
- 完整的数据分析流程

### 请求格式
```json
POST /api/v1/query
Content-Type: application/json

{
  "query": "2024年总销售额是多少？",
  "connection_id": "数据源连接ID（必需）",
  "enable_cache": false,
  "force_refresh": true,
  "stream": false
}
```

### 响应格式 (QueryResponseV3)
```json
{
  "query_id": "uuid",
  "tenant_id": "tenant_id",
  "original_query": "2024年总销售额是多少？",
  "generated_sql": "SELECT SUM(amount) FROM sales WHERE year = 2024",
  "results": [
    {"total_sales": 3256789.00}
  ],
  "row_count": 1,
  "processing_time_ms": 1250,
  "confidence_score": 0.95,
  "explanation": "根据查询结果，2024年的总销售额为3,256,789.00元。",
  "processing_steps": [
    {"step": 1, "title": "理解问题", "status": "completed"},
    {"step": 2, "title": "生成SQL", "status": "completed"},
    {"step": 3, "title": "执行查询", "status": "completed"},
    {"step": 4, "title": "生成图表", "status": "completed"}
  ],
  "echarts_option": {
    "title": {"text": "2024年总销售额"},
    "series": [...]
  }
}
```

### 特点
- ✅ 返回实际查询结果
- ✅ 支持ECharts图表生成
- ✅ 完整的处理步骤展示
- ✅ 置信度评分
- ❌ 响应速度较慢（包含DB查询）
- ❌ 需要有效的数据源连接

### 适用场景
- 生产环境数据分析
- 需要实际查询结果的场景
- 数据可视化需求
- 端到端的数据分析流程

---

## connection_id 的关键作用

`connection_id` 是 SQL 执行的前提条件：

```python
# 后端代码 (query.py)
database_url = await data_source_service.get_decrypted_connection_string(
    data_source_id=request.connection_id,  # 🔴 需要connection_id
    tenant_id=tenant.id,
    db=db
)

agent_response = await run_agent_query(
    question=question,
    database_url=database_url,  # 🔴 Agent使用这个URL连接数据库
    ...
)
```

**没有 connection_id = 没有数据库连接 = 无法执行SQL**

---

## 执行流程对比

### chat/completions 流程
```
用户问题 → 获取Schema → LLM生成 → 返回文本（含SQL）
                                           ↓
                                      不执行SQL ❌
```

### query 流程
```
用户问题 + connection_id
       ↓
    验证数据源
       ↓
  获取数据库连接
       ↓
  Agent生成SQL
       ↓
   **执行SQL** ✅  ← 关键差异
       ↓
  返回实际结果
       ↓
  生成图表配置
```

---

## 前端调用示例

### 正确的调用方式 (使用 /api/v1/query)

```typescript
// frontend/src/store/chatStore.ts
const queryRequest: ChatQueryRequest = {
  query: content,                    // 用户问题
  connection_id: finalConnectionId,  // 🔴 必需：数据源ID
  session_id: sessionId,
  history: historyMessages,
  context: { data_sources: dataSourceIds }
}

const response = await api.chat.sendQuery(queryRequest)
```

### 错误的调用方式 (使用 /api/v1/llm/chat/completions)

```typescript
// ❌ 这不会执行SQL，只返回SQL文本
const payload = {
  messages: [{ role: "user", content: question }],
  stream: false
}

const response = await fetch('/api/v1/llm/chat/completions', {
  method: 'POST',
  body: JSON.stringify(payload)
})
```

---

## 测试指南

### 使用正确的端点进行测试

#### ✅ 正确测试 (使用 /api/v1/query)
```bash
curl -X POST http://localhost:8004/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "2024年总销售额",
    "connection_id": "your_data_source_id"
  }'

# 返回：实际查询结果 + 图表配置 ✅
```

#### ❌ 错误测试 (使用 /api/v1/llm/chat/completions)
```bash
curl -X POST http://localhost:8004/api/v1/llm/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "2024年总销售额"}]
  }'

# 返回：只有SQL和解释，无实际数据 ❌
```

---

## 安全设计考虑

系统采用分层安全设计：

```
Layer 1: chat/completions（低风险）
- 只生成SQL，不执行
- 无需数据库连接
- 可以自由测试

Layer 2: query（中风险）
- 需要有效的connection_id授权
- 连接字符串加密存储
- SQL注入防护（只允许SELECT）
- 租户隔离
```

---

## 常见问题

### Q1: 为什么测试时只返回SQL而不返回结果？
**A**: 你可能使用了错误的API端点。请确保使用 `/api/v1/query` 并提供有效的 `connection_id`。

### Q2: 如何获取 connection_id？
**A**: 通过数据源管理API获取：
```bash
GET /api/v1/data-sources
```

### Q3: 两个端点可以同时使用吗？
**A**: 可以。`chat/completions` 用于快速预览，`query` 用于实际执行。

### Q4: 前端应该使用哪个端点？
**A**: 生产环境应该使用 `/api/v1/query`，以提供完整的数据分析体验。

---

## 相关文件

- `backend/src/app/api/v1/endpoints/llm.py` - chat/completions端点实现
- `backend/src/app/api/v1/endpoints/query.py` - query端点实现
- `frontend/src/store/chatStore.ts` - 前端API调用逻辑
- `scripts/run_agent_test.py` - 测试脚本（已更新为使用query端点）

---

**文档版本**: v1.0
**最后更新**: 2026-01-25
**维护者**: Data Agent Team
