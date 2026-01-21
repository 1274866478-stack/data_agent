# SOTA ChatBI 重构 - 待办事项清单

## 1. 高优先级任务 (P0)

### 1.1 修复 Qdrant Client 兼容性
- [ ] 更新 `qdrant_service.py` 使用新的 REST 客户端
- [ ] 更新 `few_shot_rag/qdrant_service.py` 使用 REST 客户端
- [ ] 移除对 qdrant-client 库的依赖
- [ ] 重新测试完整流程

### 1.2 启用 SOTA Agent
- [ ] 在 `.env` 中设置 `USE_SOTA_AGENT=true`
- [ ] 启动后端服务并验证 SOTA 端点可用
- [ ] 测试 `/api/v1/query/sota` 端点
- [ ] 测试 `/api/v1/query/sota/clarify` 端点

## 2. 配置任务 (P1)

### 2.1 创建 Cube Schema 定义
- [ ] 分析现有数据源结构
- [ ] 为每个数据源创建 Cube 定义文件
- [ ] 配置度量 (measures)
- [ ] 配置维度 (dimensions)
- [ ] 测试 Cube API 查询

示例 Cube 定义位置: `cube_schema/`

```yaml
# cube_schema/Orders.yaml
cubes:
  - name: Orders
    sql_table: orders
    measures:
      - name: total_revenue
        sql: ${amount}
        type: sum
    dimensions:
      - name: created_at
        sql: created_at
        type: time
```

### 2.2 数据库迁移
- [ ] 备份现有 ChromaDB 数据
- [ ] 执行 `migrate_chroma_to_qdrant.py`
- [ ] 验证迁移结果
- [ ] 测试向量检索功能

## 3. 测试任务 (P1)

### 3.1 单元测试
- [ ] Router Agent 单元测试
- [ ] Planner Agent 单元测试
- [ ] Generator Agent 单元测试
- [ ] Critic Agent 单元测试
- [ ] Repair Agent 单元测试

### 3.2 集成测试
- [ ] 完整查询流程测试
- [ ] 多轮对话测试
- [ ] 消歧流程测试
- [ ] 自愈流程测试
- [ ] 多租户隔离测试

### 3.3 性能测试
- [ ] 查询响应时间基准测试 (目标: P95 < 5s)
- [ ] 并发查询测试
- [ ] 内存使用测试
- [ ] Qdrant 检索性能测试

## 4. 前端集成 (P1)

### 4.1 前端适配
- [ ] 更新查询 API 调用以支持 `/query/sota`
- [ ] 实现消歧问题 UI 组件
- [ ] 显示查询复杂度和置信度
- [ ] 显示 DSL 生成结果（调试模式）

### 4.2 新功能 UI
- [ ] 澄清问题对话框
- [ ] 查询进度指示器（显示 Agent 状态）
- [ ] DSL 编辑器（高级用户）
- [ ] 查询历史详情页

## 5. 文档任务 (P2)

### 5.1 用户文档
- [ ] SOTA Agent 功能介绍
- [ ] 澄清问题交互说明
- [ ] Cube Schema 配置指南
- [ ] API 使用示例

### 5.2 开发文档
- [ ] 多智能体架构说明
- [ ] Agent 开发指南
- [ ] 业务规则配置指南
- [ ] 错误模式扩展指南

## 6. 优化任务 (P2)

### 6.1 性能优化
- [ ] Cube.js 查询缓存优化
- [ ] 向量检索缓存
- [ ] Prompt 模板缓存
- [ ] Agent 并行执行优化

### 6.2 质量优化
- [ ] 增加业务规则覆盖
- [ ] 扩展错误模式库
- [ ] 优化消歧关键词
- [ ] 改进 Prompt 模板

## 7. 运维任务 (P2)

### 7.1 监控
- [ ] 添加 Agent 执行时间监控
- [ ] 添加 Qdrant 性能监控
- [ ] 添加 Cube.js 查询监控
- [ ] 配置告警规则

### 7.2 日志
- [ ] LangSmith 集成（Agent 追踪）
- [ ] 结构化日志输出
- [ ] 查询执行日志
- [ ] 错误修复日志

## 8. 可选任务 (P3)

### 8.1 高级功能
- [ ] 多数据源联合查询
- [ ] 自定义 DSL 函数
- [ ] 查询结果导出
- [ ] 定时查询任务

### 8.2 实验性功能
- [ ] 用户反馈学习循环
- [ ] 自动 Cube Schema 推断
- [ ] 多模态查询支持
- [ ] 自然语言 DSL 编辑

---

## 立即可执行的任务

### 任务 1: 测试 SOTA API 端点
```bash
# 1. 启用 SOTA Agent
echo "USE_SOTA_AGENT=true" >> .env
echo "ENABLE_SEMANTIC_LAYER=true" >> .env

# 2. 重启后端服务
docker-compose restart backend

# 3. 测试查询端点
curl -X POST http://localhost:8004/api/v1/query/sota \
  -H "Content-Type: application/json" \
  -d '{
    "query": "最近7天的销售额",
    "tenant_id": "test_tenant"
  }'
```

### 任务 2: 创建示例 Cube Schema
```bash
# 查看现有数据源结构
psql $DATABASE_URL -c "\d orders"

# 创建 Cube 定义
cat > cube_schema/Orders.yaml << EOF
cubes:
  - name: Orders
    sql_table: orders
    measures:
      - name: total_amount
        sql: amount
        type: sum
      - name: order_count
        sql: id
        type: count
    dimensions:
      - name: created_at
        sql: created_at
        type: time
      - name: status
        sql: status
        type: string
EOF
```

### 任务 3: 执行向量数据迁移
```bash
# 备份现有数据
docker exec dataagent-chroma tar czf /chroma_backup.tar.gz /chroma/chroma
docker cp dataagent-chroma:/chroma_backup.tar.gz ./backups/

# 执行迁移
cd backend
python scripts/migrate_chroma_to_qdrant.py --verify

# 验证迁移
python scripts/test_qdrant_rest.py
```

---

## 进度跟踪

| 类别 | 完成 | 待办 | 进度 |
|------|------|------|------|
| Phase 1-5 核心实现 | 5 | 0 | 100% |
| 修复兼容性问题 | 0 | 1 | 0% |
| 配置和部署 | 0 | 2 | 0% |
| 测试 | 1 | 3 | 25% |
| 前端集成 | 0 | 4 | 0% |
| 文档 | 0 | 4 | 0% |
| 优化 | 0 | 4 | 0% |
| 运维 | 0 | 4 | 0% |
| 可选 | 0 | 4 | 0% |

---

## 推荐执行顺序

### 第1周: 核心功能验证
1. 修复 Qdrant 兼容性
2. 启用 SOTA Agent
3. 测试基础查询流程

### 第2周: 配置和优化
1. 创建 Cube Schema
2. 执行数据迁移
3. 性能基准测试

### 第3周: 前端和文档
1. 前端适配
2. 用户文档编写
3. API 文档更新

### 第4周: 优化和上线
1. 监控配置
2. 日志完善
3. 生产部署
