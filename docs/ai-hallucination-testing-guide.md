# AI助手编造数据问题 - 快速测试指南

## 概述

本文档提供快速测试指南，帮助诊断AI助手编造数据的问题。

## 快速开始

### 1. 运行测试脚本

```bash
# 运行所有测试
python scripts/test_ai_hallucination.py all

# 运行特定测试
python scripts/test_ai_hallucination.py tool_calls      # 测试工具调用
python scripts/test_ai_hallucination.py agent_simple     # 测试简单Agent查询
python scripts/test_ai_hallucination.py data_consistency # 测试数据一致性
```

### 2. 查看测试报告

测试完成后，报告会保存在：
```
docs/test_reports/ai_hallucination_test_YYYYMMDD_HHMMSS.txt
```

## 测试内容说明

### 测试1: 工具调用验证

**目的**：验证数据库工具是否可以正常调用

**检查项**：
- ✅ `list_tables` 工具是否正常工作
- ✅ `get_schema` 工具是否正常工作
- ✅ `execute_sql_safe` 工具是否正常工作

**如果失败**：
- 检查数据库连接配置
- 检查MCP服务器是否运行
- 查看错误日志

### 测试2: 简单Agent查询

**目的**：验证Agent是否可以执行简单查询

**测试问题**：
- "数据库中有哪些表？"

**检查项**：
- ✅ Agent是否返回了回答
- ✅ Agent是否调用了工具
- ✅ 回答是否基于真实数据

**如果失败**：
- 检查Agent服务是否正常运行
- 检查System Prompt是否正确加载
- 查看Agent执行日志

### 测试3: 数据一致性验证

**目的**：验证AI回答中的数据是否与数据库真实数据一致

**测试问题**：
- "查询用户表中的前5条记录"

**检查项**：
- ✅ AI是否执行了SQL查询
- ✅ AI回答中的数据是否与数据库数据一致
- ✅ AI是否编造了数据

**如果发现编造数据**：
- 查看详细日志，找出问题根源
- 检查工具返回的数据是否正确传递
- 检查Prompt是否足够强制

## 手动测试步骤

### 步骤1: 检查数据库连接

```python
# 在Python交互环境中
from backend.src.app.core.config import settings
print(settings.database_url)
```

### 步骤2: 手动测试工具调用

```python
from backend.src.app.services.agent.tools import list_available_tables

# 测试列出表
result = list_available_tables.invoke({})
print(result)
```

### 步骤3: 测试Agent查询

```python
from backend.src.app.services.agent.agent_service import run_agent
import asyncio

async def test():
    result = await run_agent(
        question="数据库中有哪些表？",
        database_url="your_database_url",
        thread_id="test",
        verbose=True
    )
    print(result)

asyncio.run(test())
```

### 步骤4: 对比数据

1. 手动执行SQL查询，获取真实数据
2. 通过Agent执行相同查询
3. 对比AI回答中的数据与真实数据
4. 检查是否一致

## 常见问题诊断

### 问题1: 工具调用失败

**症状**：测试显示工具调用失败

**可能原因**：
- MCP服务器未启动
- 数据库连接配置错误
- 网络问题

**解决方法**：
1. 检查MCP服务器状态
2. 验证数据库连接字符串
3. 查看详细错误日志

### 问题2: AI没有调用工具

**症状**：AI直接生成回答，没有调用工具

**可能原因**：
- System Prompt未正确加载
- 工具未正确绑定到LLM
- LLM模型问题

**解决方法**：
1. 检查System Prompt内容
2. 验证工具是否正确加载
3. 查看Agent初始化日志

### 问题3: AI编造数据

**症状**：AI回答中的数据与数据库不一致

**可能原因**：
- 工具返回的数据未被正确使用
- Prompt不够强制
- LLM模型倾向于生成看似合理的答案

**解决方法**：
1. 检查工具返回的数据是否正确传递
2. 强化Prompt中的防编造规则
3. 考虑调整LLM参数（temperature=0）

## 详细测试计划

完整的测试计划请参考：
[AI助手编造数据问题诊断测试计划](./ai-hallucination-diagnosis-plan.md)

## 下一步

根据测试结果：
1. 如果发现问题，记录到问题跟踪系统
2. 根据问题根源，制定修复计划
3. 执行修复后，重新运行测试验证

## 需要帮助？

如果测试过程中遇到问题：
1. 查看测试报告中的详细错误信息
2. 检查系统日志
3. 参考完整测试计划文档

