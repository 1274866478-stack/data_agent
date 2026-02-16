# Agent质量保证快速开始指南

**目标**: 3分钟内验证AI分析功能是否稳定可靠

---

## 第1步：运行基础测试（30秒）

### Windows
```bash
cd C:\data_agent\Agent
python -m pytest tests/unit/test_golden_cases.py -v
```

### 期望结果
```
==================== 18 passed in 0.05s ====================
✅ 所有测试通过
```

---

## 第2步：运行演示系统（可选，需要真实数据库）

```bash
cd Agent
python demo_qa_system.py
```

### 选项说明
- **选项1**: 运行单个测试 - 快速验证基本功能
- **选项2**: 运行完整套件 - 7个黄金测试用例
- **选项3**: 生成错误报告 - 查看历史问题统计
- **选项4**: 全部运行 - 完整验证流程

---

## 第3步：查看质量报告

### 查看错误统计
```bash
cd Agent
python -c "from error_tracker import error_tracker; print(error_tracker.generate_report(7))"
```

### 输出示例
```
# Agent错误分析报告

统计周期: 最近 7 天

总体概况
- 总请求数: 100
- 成功请求: 95
- 失败请求: 5
- 成功率: 95.00%

错误分类统计
- 表或字段不存在: 3 (60%)
- 用户问题不明确: 2 (40%)
```

---

## 如何判断系统质量合格？

### ✅ 合格标准
- [ ] 单元测试通过率 = 100% (18/18)
- [ ] 成功率 >= 95% (最近7天)
- [ ] P0测试用例 100% 通过
- [ ] 无P0级别的已知Bug

### ⚠️ 需要改进
- 成功率 80-95%
- 有P1测试用例失败
- 错误主要是边界情况

### ❌ 不合格
- 成功率 < 80%
- 有P0测试用例失败
- 安全测试失败

---

## 日常使用建议

### 每次代码修改后
```bash
# 快速测试（10秒）
cd Agent
pytest tests/unit -v -k "not slow"
```

### 每天下班前
```bash
# 查看今日错误
python -c "from error_tracker import error_tracker; stats = error_tracker.get_error_stats(1); print(f'今日成功率: {stats[\"success_rate\"]}')"
```

### 每周五
```bash
# 生成周报
python demo_qa_system.py
# 选择 3 - 生成错误分析报告
```

---

## 集成到现有代码

### 在后端API中使用（推荐）

编辑 `backend/src/app/api/v1/endpoints/query.py`:

```python
from Agent.sql_agent import run_agent_with_tracking

@router.post("/natural-query")
async def natural_language_query(
    question: str,
    tenant_id: str,
    user_id: str
):
    result = await run_agent_with_tracking(
        question=question,
        context={
            "tenant_id": tenant_id,
            "user_id": user_id
        }
    )
    return result
```

### 好处
- ✅ 自动记录所有错误
- ✅ 性能监控
- ✅ 用户问题分析
- ✅ 成功率实时统计

---

## 常见问题

### Q1: 测试运行失败？
**A**: 检查Python环境和依赖
```bash
cd Agent
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Q2: 错误追踪没有数据？
**A**: 需要先运行一些查询
```bash
python demo_qa_system.py
# 选择1或2运行测试
```

### Q3: 如何清空错误日志？
**A**: 删除日志文件
```bash
del agent_errors.jsonl
del agent_success.jsonl
```

### Q4: 测试用例太少？
**A**: 添加更多测试到 `tests/conftest.py` 的 `golden_test_cases`

---

## 下一步

1. ✅ **已完成**: 测试框架搭建
2. ✅ **已完成**: 错误追踪集成
3. 🔄 **进行中**: 累积真实错误数据
4. ⏭️ **待做**: 基于错误数据优化Prompt
5. ⏭️ **待做**: 扩充测试用例库

---

## 获取帮助

- 查看完整文档: `docs/QA/ai-analysis-qa-strategy.md`
- 查看测试清单: `docs/QA/ai-analysis-verification-checklist.md`
- 查看测试指南: `docs/QA/quick-start-testing-guide.md`

---

**最后更新**: 2025-01-06
**维护者**: QA Team
