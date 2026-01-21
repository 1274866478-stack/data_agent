# SOTA ChatBI MVP 验证清单

## 最小可行步骤（约 2-3 小时）

### Step 1: 修复 Qdrant 兼容性 (30分钟)

```bash
# 1. 更新 few_shot_rag/qdrant_service.py
# 将 QdrantClient 替换为 QdrantRESTClient

# 2. 运行测试验证
python backend/scripts/test_qdrant_rest.py
```

### Step 2: 创建示例 Cube Schema (1小时)

```yaml
# cube_schema/Orders.yaml
cubes:
  - name: Orders
    sql_table: orders
    measures:
      - name: total_amount
        sql: amount
        type: sum
    dimensions:
      - name: created_at
        sql: created_at
        type: time
```

### Step 3: 端到端测试 (30分钟)

```bash
# 1. 启用 SOTA Agent
echo "USE_SOTA_AGENT=true" >> .env

# 2. 重启服务
docker-compose restart backend

# 3. 测试查询
curl -X POST http://localhost:8004/api/v1/query/sota \
  -H "Content-Type: application/json" \
  -d '{"query": "最近7天的销售额"}'
```

---

## 预期结果

✅ 成功标志：
- Qdrant 测试通过（REST API 可用）
- Cube.js 可以查询数据
- SOTA 端点返回查询结果
- Agent 工作流执行成功

❌ 失败标志：
- 502 错误 → Qdrant 兼容性问题未解决
- 空结果 → Cube Schema 配置错误
- Agent 报错 → 配置或依赖问题

---

## 如果失败怎么办？

| 问题 | 检查点 |
|------|--------|
| Qdrant 502 | 使用 qdrant_rest_client.py |
| Cube 无数据 | 检查 sql_table 和字段名 |
| Agent 不工作 | 检查 .env 配置 |
| API 404 | 检查 /query/sota 路由 |
