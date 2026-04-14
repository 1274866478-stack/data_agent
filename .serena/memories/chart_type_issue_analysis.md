# 图表类型问题分析报告

## 问题描述
用户问题"各电子产品的销售占比情况"包含"占比"关键词，应该触发饼图，但实际返回了柱状图。

## 调查结果

### 1. 图表类型推断逻辑位置

**主要推断函数**：
- `data_validator.py` 的 `recommend_chart()` 函数（第445行）
- `data_validator.py` 的 `_detect_percentage_data()` 函数（第392行）
- `agent_service.py` 的回退推断逻辑（第2862-2868行）

### 2. 占比关键词判断逻辑

**在 recommend_chart() 中**（第491-498行）：
```python
# 占比类 -> 饼图
if any(kw in question_lower for kw in [
    "占比", "分布", "比例", "份额"
]):
    if len(query_results) <= 8:
        chart_type = "pie"
        reasoning.append("用户问题包含占比关键词，且类别数量适中")
```

**问题**：这个逻辑有**数量限制**（`<= 8`），如果电子产品类别超过8个，就不会选择饼图！

**在回退逻辑中**（第2867行）：
```python
elif any(kw in question_lower for kw in ["占比", "分布", "比例"]):
    inferred_type = "pie"
```
这个逻辑没有数量限制。

### 3. _detect_percentage_data 函数

这个函数检测百分比数据的特征：
1. 检查列名是否包含百分比关键词
2. 检查数值特征：总和接近100，且所有值在0-100范围内

**问题**：如果数据不是百分比格式（如实际销量数值），这个函数会返回 False。

### 4. 可能的问题原因

**主要原因**：
1. **数量限制问题**：`recommend_chart()` 函数中，当数据超过8个类别时，即使包含"占比"关键词也不会选择饼图
2. **数据格式问题**：如果返回的是销售数值而不是百分比，可能触发其他推断逻辑

**次要原因**：
1. 字段映射可能影响最终的图表生成
2. LLM生成的图表配置可能被优先使用

### 5. 建议修复方案

1. **移除类别数量限制**：对于包含占比关键词的问题，应该始终推荐饼图
2. **增强百分比检测**：更好地识别占比类数据
3. **优先级调整**：确保问题关键词的优先级高于数据特征推断

### 6. 涉及文件

- `backend/src/app/services/agent/data_validator.py` - 主要推断逻辑
- `backend/src/app/services/agent/agent_service.py` - 图表生成和回退逻辑
- `backend/src/app/services/agent/prompts.py` - 系统提示词（包含占比处理规则）
- `frontend/src/lib/api-client.ts` - 前端图表类型定义