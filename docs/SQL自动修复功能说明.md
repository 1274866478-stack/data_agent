# SQL自动修复功能说明

## 📋 功能概述

当AI助手生成的SQL查询执行失败时（例如列名错误、表名错误等），系统会**自动使用AI修复SQL并重试**，无需用户手动干预。

## 🎯 解决的问题

### 问题场景
用户询问："库存最多的产品是什么？"

AI生成的SQL：
```sql
SELECT name, stock
FROM products
ORDER BY stock DESC
LIMIT 1;
```

**执行失败**：`column "stock" does not exist`

### 传统处理方式
- ❌ 显示错误信息给用户
- ❌ 用户需要手动查看schema
- ❌ 用户需要重新提问或修改问题
- ❌ 体验差，效率低

### 新的智能处理方式
- ✅ 系统自动捕获错误
- ✅ AI分析错误信息和schema
- ✅ 自动生成修复后的SQL
- ✅ 自动重试执行
- ✅ 最多重试2次
- ✅ 成功后显示结果，并标注"已自动修复"

---

## 🔧 技术实现

### 核心流程

```
用户提问
    ↓
AI生成SQL
    ↓
执行SQL
    ↓
失败？ ──否──→ 返回结果
    ↓
   是
    ↓
调用AI修复SQL
    ↓
重新执行
    ↓
成功？ ──是──→ 返回结果 + "已自动修复"标记
    ↓
   否
    ↓
重试次数 < 2？ ──是──→ 继续修复
    ↓
   否
    ↓
返回错误 + 修复尝试次数
```

### 关键函数

#### 1. `_fix_sql_with_ai()`
**位置**: `backend/src/app/api/v1/endpoints/llm.py`

**功能**: 使用AI修复失败的SQL查询

**参数**:
- `original_sql`: 原始失败的SQL
- `error_message`: 数据库返回的错误信息
- `schema_context`: 完整的数据库schema信息
- `original_question`: 用户的原始问题

**返回**: 修复后的SQL，如果无法修复则返回None

**工作原理**:
1. 构建包含错误信息和schema的提示词
2. 调用智谱AI分析错误原因
3. 基于正确的schema生成修复后的SQL
4. 验证修复后的SQL安全性
5. 返回修复后的SQL

#### 2. `_execute_sql_if_needed()` (增强版)
**位置**: `backend/src/app/api/v1/endpoints/llm.py`

**新增功能**:
- 智能重试机制（最多2次）
- 自动调用AI修复失败的SQL
- 显示修复过程和结果

**执行流程**:
```python
for sql_query in sql_matches:
    current_sql = sql_query.strip()
    retry_count = 0
    max_retries = 2
    
    while retry_count <= max_retries:
        try:
            # 执行SQL
            result = await adapter.execute_query(connection_string, current_sql)
            # 成功 - 返回结果
            break
        except Exception as e:
            # 失败 - 尝试修复
            if retry_count < max_retries:
                fixed_sql = await _fix_sql_with_ai(...)
                if fixed_sql:
                    current_sql = fixed_sql
                    retry_count += 1
                    continue
            break
```

---

## 📊 使用示例

### 示例1：列名错误自动修复

**用户问题**: "库存最多的产品是什么？"

**AI初次生成的SQL**:
```sql
SELECT name, stock
FROM products
ORDER BY stock DESC
LIMIT 1;
```

**执行结果**: ❌ `column "stock" does not exist`

**AI自动修复后的SQL**:
```sql
SELECT name, inventory_quantity
FROM products
ORDER BY inventory_quantity DESC
LIMIT 1;
```

**最终显示**:
```
🔧 SQL已自动修复：
```sql
SELECT name, inventory_quantity
FROM products
ORDER BY inventory_quantity DESC
LIMIT 1;
```

📊 查询结果：
- 返回行数：1
- 执行时间：0.05秒

| name | inventory_quantity |
|------|-------------------|
| 产品A | 500 |

✅ SQL已自动修复（重试1次后成功）
```

### 示例2：表名错误自动修复

**用户问题**: "有多少订单？"

**AI初次生成的SQL**:
```sql
SELECT COUNT(*) as total
FROM order
```

**执行结果**: ❌ `relation "order" does not exist`

**AI自动修复后的SQL**:
```sql
SELECT COUNT(*) as total
FROM orders
```

**最终显示**: 成功返回结果，并标注"已自动修复"

---

## ⚙️ 配置参数

### 重试次数
```python
max_retries = 2  # 最多重试2次
```

### AI修复参数
```python
temperature=0.1  # 低温度确保准确性
max_tokens=1000  # 足够生成完整SQL
```

---

## 🎨 用户体验优化

### 成功修复时
- ✅ 显示修复后的SQL
- ✅ 显示查询结果
- ✅ 标注"已自动修复（重试X次后成功）"

### 修复失败时
- ❌ 显示原始错误信息
- ❌ 显示尝试修复的次数
- 💡 提供建议："请检查表名和列名是否正确，或查看数据源的schema信息"

---

## 🔒 安全性

### SQL验证
- ✅ 只允许SELECT查询
- ✅ 禁止UPDATE、DELETE、DROP等危险操作
- ✅ 检查SQL注入风险
- ✅ 验证表名和列名存在于schema中

### 错误处理
- ✅ 捕获所有异常
- ✅ 记录详细日志
- ✅ 防止无限重试
- ✅ 超时保护

---

## 📈 性能影响

### 正常情况（SQL正确）
- 执行时间：无额外开销
- 响应时间：与之前相同

### 需要修复的情况
- 第1次重试：+1-2秒（AI修复时间）
- 第2次重试：+1-2秒（AI修复时间）
- 总计最多：+4秒

### 优化措施
- 使用低温度参数（0.1）提高修复准确率
- 限制最大重试次数（2次）
- 异步执行，不阻塞其他请求

---

## 🚀 未来改进方向

1. **学习机制**: 记录常见错误和修复方案，建立知识库
2. **预测性修复**: 在生成SQL时就参考历史错误，减少失败率
3. **用户反馈**: 允许用户确认修复后的SQL是否符合预期
4. **性能优化**: 缓存schema信息，减少重复获取
5. **多语言支持**: 支持MySQL、SQLite等其他数据库

---

**更新时间**: 2025-11-30
**版本**: V4.1
**作者**: AI Assistant

