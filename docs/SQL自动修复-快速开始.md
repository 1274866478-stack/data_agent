# SQL自动修复功能 - 快速开始

## 🎯 问题描述

你遇到的问题：AI助手生成的SQL使用了错误的列名 `stock`，但实际数据库中该列不存在，导致查询失败。

**原始错误**:
```
❌ 查询执行失败: column "stock" does not exist
```

## ✅ 解决方案

我已经为系统添加了**智能SQL自动修复功能**。现在当SQL执行失败时，系统会：

1. **自动捕获错误** - 识别SQL执行失败
2. **AI分析错误** - 将错误信息和数据库schema发送给AI
3. **生成修复方案** - AI基于正确的schema重新生成SQL
4. **自动重试** - 使用修复后的SQL重新执行
5. **最多重试2次** - 避免无限循环

## 🚀 如何使用

### 无需任何操作！

这个功能是**完全自动的**，你不需要做任何配置或修改。

只需要像之前一样向AI助手提问：

```
用户: 库存最多的产品是什么？
```

### 系统会自动处理

#### 场景1：SQL正确（无变化）
如果AI生成的SQL是正确的，系统会直接执行并返回结果，和之前一样。

#### 场景2：SQL错误（自动修复）
如果AI生成的SQL有错误（如列名错误），系统会：

**第1步**: 尝试执行原始SQL
```sql
SELECT name, stock FROM products ORDER BY stock DESC LIMIT 1;
```
❌ 失败：`column "stock" does not exist`

**第2步**: AI自动修复SQL
```sql
SELECT name, inventory_quantity FROM products ORDER BY inventory_quantity DESC LIMIT 1;
```

**第3步**: 执行修复后的SQL
✅ 成功！返回结果

**第4步**: 显示结果并标注
```
🔧 SQL已自动修复：
```sql
SELECT name, inventory_quantity FROM products ORDER BY inventory_quantity DESC LIMIT 1;
```

📊 查询结果：
| name | inventory_quantity |
|------|-------------------|
| 产品A | 500 |

✅ SQL已自动修复（重试1次后成功）
```

## 📋 支持的错误类型

### ✅ 列名错误
- 错误：`SELECT stock FROM products`
- 修复：`SELECT inventory_quantity FROM products`

### ✅ 表名错误
- 错误：`SELECT * FROM order`
- 修复：`SELECT * FROM orders`

### ✅ 列名拼写错误
- 错误：`SELECT custmer_name FROM customers`
- 修复：`SELECT customer_name FROM customers`

### ✅ 大小写问题
- 错误：`SELECT Name FROM Products`
- 修复：`SELECT name FROM products`

## 🔧 技术细节

### 修改的文件
- `backend/src/app/api/v1/endpoints/llm.py`
  - 新增 `_fix_sql_with_ai()` 函数
  - 增强 `_execute_sql_if_needed()` 函数
  - 增强 `_stream_response_generator()` 函数

### 关键参数
```python
max_retries = 2          # 最多重试2次
temperature = 0.1        # AI修复时使用低温度确保准确性
max_tokens = 1000        # 足够生成完整SQL
```

## 🎨 用户体验

### 成功修复
- ✅ 显示修复后的SQL
- ✅ 显示查询结果
- ✅ 标注修复次数

### 无法修复
- ❌ 显示原始错误
- ❌ 显示尝试次数
- 💡 提供建议

## 🔒 安全性

- ✅ 只允许SELECT查询
- ✅ 禁止危险操作（UPDATE、DELETE、DROP等）
- ✅ 验证修复后的SQL安全性
- ✅ 限制最大重试次数

## 📊 性能影响

- **SQL正确时**: 无额外开销
- **需要修复时**: 每次重试增加1-2秒
- **最多延迟**: 4秒（2次重试）

## 🧪 测试建议

### 测试场景1：列名错误
```
问题: "库存最多的产品是什么？"
预期: 系统自动修复列名并返回正确结果
```

### 测试场景2：表名错误
```
问题: "有多少订单？"
预期: 系统自动修复表名并返回正确结果
```

### 测试场景3：复杂查询
```
问题: "每个类别的平均价格是多少？"
预期: 系统自动修复列名/表名并返回正确结果
```

## 📝 日志查看

如果想查看修复过程，可以查看后端日志：

```bash
# 查看后端日志
docker logs data_agent_backend -f

# 关键日志信息
[INFO] 检测到 1 个SQL查询，准备执行
[ERROR] 执行SQL查询失败 (尝试 1/3): column "stock" does not exist
[INFO] 尝试使用AI修复SQL...
[INFO] AI成功修复SQL: SELECT name, inventory_quantity FROM...
[INFO] SQL查询执行成功，返回 1 行
```

## 🎉 总结

现在你可以直接向AI助手提问，即使AI生成的SQL有小错误（如列名错误），系统也会**自动修复并重试**，无需你手动干预！

这大大提升了用户体验，减少了因为schema不匹配导致的查询失败。

---

**更新时间**: 2025-11-30
**版本**: V4.1
**作者**: AI Assistant

