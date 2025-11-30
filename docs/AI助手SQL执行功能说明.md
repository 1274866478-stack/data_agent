# AI助手SQL执行功能说明

## 📋 功能概述

AI助手现在具备**自动SQL生成和执行**功能。当用户询问数据相关问题时，AI会：

1. 🧠 **理解问题** - 分析用户的自然语言查询
2. 📝 **生成SQL** - 基于数据库schema生成准确的SQL查询
3. ⚡ **执行查询** - 自动连接数据库并执行SQL
4. 📊 **返回结果** - 展示实际的查询结果和数据分析
5. 💡 **提供洞察** - 基于真实数据给出业务建议

---

## 🔧 技术实现

### 架构设计

```
用户提问
    ↓
AI生成SQL（智谱GLM-4-flash）
    ↓
后端检测SQL代码块
    ↓
自动执行SQL查询
    ↓
将结果插入AI回复
    ↓
返回增强后的回复
```

### 核心代码

**文件**: `backend/src/app/api/v1/endpoints/llm.py`

**关键函数**:
- `_execute_sql_if_needed()` - 检测并执行SQL查询
- `_build_system_prompt_with_context()` - 构建包含数据源信息的系统提示词

**工作流程**:
1. AI生成包含SQL代码块的回复
2. 后端使用正则表达式检测 ` ```sql ... ``` ` 代码块
3. 验证SQL安全性（只允许SELECT查询）
4. 连接数据库并执行查询
5. 格式化查询结果为Markdown表格
6. 将结果插入到原始回复中

---

## 🎯 使用示例

### 示例1：简单聚合查询

**用户问题**: "2024年总销售额是多少？"

**AI回答**:
```
根据数据库查询结果：

**2024年总销售额：¥685,449.00**

**SQL查询：**
```sql
SELECT SUM(total_amount) as total_sales
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2024
  AND status != 'cancelled';
```

**📊 查询结果：**

- 返回行数：1
- 执行时间：0.05秒

**数据预览（前5行）：**

| total_sales |
|---|
| 685449.00 |

**分析：**
2024年的总销售额为¥685,449.00，表明公司在该年度的销售表现良好。
```

### 示例2：复杂分析查询

**用户问题**: "哪个销售人员的业绩最好？"

**AI回答**:
```
**SQL查询：**
```sql
SELECT 
    e.name as employee_name,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as total_sales
FROM employees e
LEFT JOIN orders o ON e.id = o.employee_id
WHERE EXTRACT(YEAR FROM o.order_date) = 2024
GROUP BY e.id, e.name
ORDER BY total_sales DESC
LIMIT 5;
```

**📊 查询结果：**

| employee_name | order_count | total_sales |
|---|---|---|
| 张伟 | 8 | 156,800.00 |
| 李娜 | 7 | 142,300.00 |
| 王强 | 6 | 128,500.00 |

**分析：**
张伟是2024年业绩最好的销售人员，完成了8笔订单，总销售额达¥156,800。
```

---

## ⚙️ 配置要求

### 1. 环境变量

在 `.env` 文件中添加：

```bash
# 数据加密密钥（用于加密数据库连接字符串）
ENCRYPTION_KEY=V1ZvT09XWm5MWDl4aHNwamIwOFUwX0ZSdlNfclNTVnUxMmM5cTViaVVOdz0=

# 智谱AI API密钥
ZHIPUAI_API_KEY=your_api_key_here
```

### 2. 数据源配置

数据源必须：
- ✅ 状态为 `ACTIVE`
- ✅ 使用正确的加密密钥加密连接字符串
- ✅ 连接字符串使用Docker内部主机名（如 `db` 而不是 `localhost`）

### 3. 数据库连接字符串格式

```
postgresql://用户名:密码@主机:端口/数据库名

示例（Docker内部）:
postgresql://postgres:password@db:5432/chatbi_test

示例（外部访问）:
postgresql://postgres:password@localhost:5432/chatbi_test
```

---

## 🔒 安全措施

1. **SQL注入防护** - 只允许SELECT查询，禁止UPDATE/DELETE/DROP等危险操作
2. **连接字符串加密** - 所有数据库连接字符串使用AES加密存储
3. **租户隔离** - 每个租户只能访问自己的数据源
4. **查询限制** - 默认限制返回100行数据

---

## 🧪 测试

### 快速测试

```bash
# 1. 设置测试数据库和数据源
python scripts/recreate-datasource-with-correct-key.py

# 2. 运行测试
python scripts/test-ai-sql-execution.py
```

### 测试问题清单

参见 `scripts/CHATBI_TEST_SETUP.md` 中的20个测试问题，涵盖：
- 基础查询（聚合、计数）
- 中级查询（多表关联）
- 高级查询（时间序列、排序）
- 业务洞察（对比分析、趋势分析）

---

## 📝 注意事项

1. **首次使用** - 需要先在数据源管理中添加数据库连接
2. **加密密钥** - 必须确保 `.env` 中的 `ENCRYPTION_KEY` 与数据源创建时使用的密钥一致
3. **Docker网络** - 后端在Docker容器内运行时，必须使用Docker网络主机名（如 `db`）
4. **查询性能** - 复杂查询可能需要较长时间，建议添加适当的索引

---

## 🐛 故障排查

### 问题1：AI生成SQL但不执行

**症状**: AI回复包含SQL代码块，但没有查询结果

**原因**: 
- 数据源未配置或状态为INACTIVE
- 连接字符串解密失败

**解决方案**:
```bash
# 重新创建数据源（使用正确的加密密钥）
python scripts/recreate-datasource-with-correct-key.py
```

### 问题2：连接字符串解密失败

**症状**: 后端日志显示 "Failed to decrypt connection string"

**原因**: `.env` 中的 `ENCRYPTION_KEY` 与数据源创建时使用的密钥不一致

**解决方案**:
1. 确保 `.env` 中有 `ENCRYPTION_KEY`
2. 重启后端服务: `docker restart dataagent-backend`
3. 重新创建数据源

### 问题3：无法连接数据库

**症状**: 查询执行失败，提示连接错误

**原因**: 连接字符串使用了错误的主机名

**解决方案**:
- Docker内部: 使用 `db` 作为主机名
- 外部访问: 使用 `localhost` 或实际IP地址

---

## 🚀 未来改进

- [ ] 支持流式SQL执行（实时显示查询进度）
- [ ] 支持SQL查询缓存（提高重复查询性能）
- [ ] 支持更多数据库类型（MySQL、MongoDB等）
- [ ] 支持SQL查询优化建议
- [ ] 支持查询结果可视化（图表生成）

---

**最后更新**: 2025-11-29
**版本**: V4.1

