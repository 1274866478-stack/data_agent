# Task Plan: ChatBI 占比查询跨表问题修复
<!--
  WHAT: 修复 ChatBI 系统中占比查询时跨表跳跃导致的数据口径不一致问题
  WHY: 用户查询"安徽的客户占比"时，AI 在 users 和 addresses 表之间跳跃，分子分母口径不一致
-->

## Goal
修复 ChatBI 系统占比查询时的表选择混乱问题，确保分子分母来自同一张表，返回完整的数据分布。

## Current Phase
Phase 1: 根本原因分析（已完成）

## 问题根因分析

| 问题 | 描述 | 严重程度 |
|------|------|----------|
| 表选择混乱 | AI 不知道 users.province 可能为空，应优先用 addresses 表 | 🔴 P0 |
| 分子分母不一致 | 分子查 users 表，分母查 addresses 表 | 🔴 P0 |
| 多次查询 | 没有使用一次 GROUP BY 查询获取完整分布 | 🟡 P1 |
| 省份名称 | 使用"安徽"而非"安徽省"导致匹配失败 | 🟡 P1 |

### 截图中的错误流程
```
步骤6: SELECT COUNT(*) FROM users WHERE province = '安徽'     ← 分子
步骤7: SELECT COUNT(*) FROM addresses WHERE province = '安徽' ← 又换表
步骤9: SELECT COUNT(*) FROM addresses                        ← 分母
```

### 正确流程
```sql
-- 一次查询获取所有省份分布
SELECT province, COUNT(*) as count
FROM addresses
GROUP BY province
ORDER BY count DESC;
```

## Phases

### Phase 1: 根本原因分析 ✅
- [x] 分析截图中的问题流程
- [x] 探索相关代码文件
- [x] 确定问题根因
- **Status:** complete

### Phase 2: 解决方案设计
- [x] 设计 Prompt 增强方案
- [x] 设计表推荐机制
- [x] 设计一致性验证机制
- **Status:** in_progress

### Phase 3: 实施修复
- [ ] 修改 AgentV2/prompt_simplified.txt
- [ ] 修改 AgentV2/tools/database_tools.py
- [ ] 修改 backend/src/app/api/v2/endpoints/query_stream_v2.py
- **Status:** pending

### Phase 4: 测试验证
- [ ] 测试 "安徽的客户占比如何"
- [ ] 测试 "各省份客户分布"
- [ ] 验证饼图显示完整数据
- **Status:** pending

### Phase 5: 部署和文档
- [ ] 重启服务
- [ ] 更新相关文档
- **Status:** pending

## Key Questions
1. **为什么 AI 选择了 users 表而不是 addresses 表？**
   - 答：AI 不知道 users.province 可能为空，需要明确表选择规则
2. **如何让 AI 知道应该优先查询 addresses 表？**
   - 答：在 Prompt 中添加表关系说明
3. **如何防止分子分母来自不同表？**
   - 答：添加一致性验证逻辑
4. **省份名称"安徽" vs "安徽省"如何处理？**
   - 答：已添加智能匹配映射，需要在 Prompt 中强调使用完整名称

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 增强 Prompt 而非修改 Agent 逻辑 | Prompt 修改更快速，LLM 可以理解表关系 |
| 添加表选择规则 | 明确告诉 AI 哪个表包含完整省份信息 |
| 添加一致性验证 | 防止 AI 从不同表获取分子分母 |
| 保持省份智能匹配 | 已有代码可处理简称→完整名称映射 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 跨表口径不一致 | 1 | 添加表选择规则到 Prompt |
| 分子分母表不同 | 1 | 添加一致性验证逻辑 |
| 省份名称简称匹配失败 | 1 | 已有智能匹配代码，需强调使用完整名称 |

## Notes
<!-- 
  REMINDERS:
  - Update phase status as you progress: pending → in_progress → complete
  - Re-read this plan before major decisions (attention manipulation)
  - Log ALL errors - they help avoid repetition
  - Never repeat a failed action - mutate your approach instead
-->
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions (attention manipulation)
- Log ALL errors - they help avoid repetition
