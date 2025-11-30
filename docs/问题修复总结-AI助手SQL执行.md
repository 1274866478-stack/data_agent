# AI助手SQL执行功能修复总结

## 📋 问题描述

用户报告AI助手在回答数据查询问题时，只生成SQL查询但不执行，并给出推测性的文字描述，而不是返回实际的查询结果。

**问题截图显示：**
- AI生成了SQL查询
- 但回复中说"目前我无法直接访问数据库以执行查询"
- 没有返回实际的查询结果

---

## 🔍 根本原因

经过排查，发现了以下问题：

### 1. 加密密钥配置问题
- **问题**：数据源连接字符串使用加密存储，但Docker容器内的后端没有正确的`ENCRYPTION_KEY`环境变量
- **表现**：后端日志显示 "Failed to decrypt connection string"
- **影响**：无法解密数据库连接字符串，导致SQL无法执行

### 2. Docker环境变量传递问题
- **问题**：`.env`文件中添加了`ENCRYPTION_KEY`，但`docker-compose.yml`没有显式声明这个环境变量
- **表现**：容器内 `env | grep ENCRYPTION` 返回空
- **影响**：即使重启容器，环境变量也没有被加载

### 3. AI提示词不够明确
- **问题**：系统提示词没有明确告诉AI，SQL会被自动执行
- **表现**：AI在生成SQL后又说"我将执行查询"或"无法访问数据库"
- **影响**：用户体验不佳，回复内容自相矛盾

---

## ✅ 解决方案

### 步骤1：添加加密密钥到.env文件

**文件**：`.env`

```bash
# 数据加密密钥（用于加密数据库连接字符串等敏感信息）
ENCRYPTION_KEY=V1ZvT09XWm5MWDl4aHNwamIwOFUwX0ZSdlNfclNTVnUxMmM5cTViaVVOdz0=
```

### 步骤2：更新docker-compose.yml

**文件**：`docker-compose.yml`

在backend服务的environment部分添加：

```yaml
environment:
  # ... 其他环境变量 ...
  - ENCRYPTION_KEY=${ENCRYPTION_KEY}  # 新增这一行
```

### 步骤3：重新创建数据源（使用正确的密钥）

**脚本**：`scripts/recreate-datasource-with-correct-key.py`

```python
# 设置环境变量（必须在导入之前）
os.environ['ENCRYPTION_KEY'] = 'V1ZvT09XWm5MWDl4aHNwamIwOFUwX0ZSdlNfclNTVnUxMmM5cTViaVVOdz0='

# 删除旧数据源
# 使用正确的密钥加密连接字符串
# 创建新数据源
```

运行：
```bash
python scripts/recreate-datasource-with-correct-key.py
```

### 步骤4：优化AI系统提示词

**文件**：`backend/src/app/api/v1/endpoints/llm.py`

关键修改：

```python
## 第3步：系统自动执行SQL
**重要：** 当你在回答中包含SQL代码块（```sql ... ```）时，系统会**自动执行**这个SQL查询并将结果插入到你的回答中。

**你只需要：**
1. 生成正确的SQL查询
2. 将SQL放在代码块中
3. 系统会自动执行并显示结果

**你不需要：**
- ❌ 说"我将执行这个查询"
- ❌ 说"我无法访问数据库"
- ❌ 说"请您自己执行这个查询"
```

### 步骤5：重启后端服务

```bash
docker-compose restart backend
# 或
docker-compose up -d backend
```

---

## 🎯 修复效果

### 修复前
```
AI回答：
为了回答您的问题，我将生成一个SQL查询...

**SQL查询：**
```sql
SELECT SUM(total_amount) FROM orders WHERE...
```

很抱歉，目前我无法直接访问数据库以执行查询...
```

### 修复后
```
AI回答：
根据数据库查询结果：

**2024年总销售额：¥660,101.00**

**SQL查询：**
```sql
SELECT SUM(total_amount) as total_sales
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2024
  AND status != 'cancelled';
```

**📊 查询结果：**
- 返回行数：1
- 执行时间：0.00秒

**数据预览（前5行）：**
| total_sales |
|---|
| 660101.00 |

**分析：**
2024年的总销售额为¥660,101.00，显示出良好的销售业绩...
```

---

## 📝 关键文件清单

| 文件路径 | 修改内容 | 作用 |
|---------|----------|------|
| `.env` | 添加 `ENCRYPTION_KEY` | 提供数据加密密钥 |
| `docker-compose.yml` | 添加 `ENCRYPTION_KEY` 环境变量 | 传递密钥到Docker容器 |
| `backend/src/app/api/v1/endpoints/llm.py` | 优化系统提示词 | 指导AI正确生成和执行SQL |
| `scripts/recreate-datasource-with-correct-key.py` | 新建脚本 | 使用正确密钥重建数据源 |
| `scripts/test-ai-sql-execution.py` | 已存在 | 测试SQL执行功能 |

---

## 🧪 测试验证

运行测试脚本：
```bash
python scripts/test-ai-sql-execution.py
```

**预期结果：**
- ✅ 包含SQL查询
- ✅ 包含查询结果
- ✅ 返回实际数据（不是推测）
- ✅ 没有"无法访问数据库"等错误提示

---

## 💡 经验教训

1. **Docker环境变量管理**
   - `env_file` 只读取文件，但不会自动传递所有变量
   - 需要在 `environment` 部分显式声明需要的变量

2. **加密密钥一致性**
   - 数据加密时使用的密钥必须与解密时使用的密钥一致
   - 密钥变更后需要重新加密所有敏感数据

3. **AI提示词设计**
   - 需要明确告诉AI系统的自动化行为
   - 避免AI产生与实际功能不符的回复

---

**修复完成时间**：2025-11-29
**修复人员**：AI Assistant
**测试状态**：✅ 通过

