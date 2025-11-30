# ChatBI 测试数据库设置指南

## ✅ 数据库已创建

测试数据库 `chatbi_test` 已成功创建并初始化，包含以下数据：

| 表名 | 记录数 | 描述 |
|------|--------|------|
| regions | 6 | 地区数据（华东、华北、华南等） |
| employees | 8 | 员工/销售人员信息 |
| categories | 5 | 产品类别 |
| products | 14 | 产品信息（iPhone、MacBook等） |
| customers | 10 | 客户信息 |
| orders | 35 | 2024年订单数据 |
| order_items | 49 | 订单明细 |

## 📊 Excel 测试数据

Excel 文件已生成：`scripts/chatbi_test_data.xlsx`
包含所有表的数据，可用于离线查看和分析。

---

## 🔧 在 Data Agent 中添加数据源

### 方法 1：通过前端界面添加（推荐）

1. **打开数据源管理页面**
   - 访问：http://localhost:3000/data-sources
   - 或点击左侧菜单的"数据源管理"

2. **点击"添加数据源"按钮**

3. **填写连接信息**
   ```
   数据源名称：ChatBI测试数据库
   数据库类型：PostgreSQL
   连接字符串：postgresql://postgres:password@db:5432/chatbi_test
   ```
   
   ⚠️ **重要**：使用 `db` 作为主机名（Docker 容器网络内的主机名），而不是 `localhost`

4. **测试连接**
   - 点击"测试连接"按钮
   - 确认显示"连接成功"

5. **保存数据源**
   - 点击"保存"或"创建"按钮

---

### 方法 2：通过 API 添加

```bash
curl -X POST "http://localhost:8004/api/v1/data-sources/?tenant_id=default_tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ChatBI测试数据库",
    "connection_string": "postgresql://postgres:password@db:5432/chatbi_test",
    "db_type": "postgresql"
  }'
```

---

## 🧪 测试 AI 助手

添加数据源后，在 AI 助手中测试以下问题：

### 基础查询
1. **2024年总销售额是多少？**
2. **我们一共有多少个客户？**
3. **库存最多的产品是什么？**
4. **销售部有多少名员工？**

### 中级查询
5. **销售额最高的产品是什么？**
6. **哪个地区的客户最多？**
7. **张伟今年完成了多少订单？**
8. **VIP客户的平均订单金额是多少？**

### 高级查询
9. **2024年每个月的销售趋势如何？**
10. **哪个销售人员的业绩最好？列出前3名**
11. **电子产品类别的利润率是多少？**
12. **哪些客户在最近3个月没有下单？**

---

## 📝 预期结果示例

### 问题：2024年总销售额是多少？

**正确的AI回答应该包含：**
```
根据数据库查询结果：

2024年总销售额：¥685,449.00

SQL查询：
SELECT SUM(total_amount) as total_sales 
FROM orders 
WHERE EXTRACT(YEAR FROM order_date) = 2024 
  AND status != 'cancelled';

详细信息：
- 订单总数：35笔
- 已完成订单：31笔
- 总折扣金额：¥24,800.00
```

**❌ 错误的回答（当前问题）：**
- 只有文字描述，没有具体数字
- 没有执行SQL查询
- 没有连接到数据库

---

## 🔍 故障排查

### 问题：AI 助手只返回文字描述，没有查询数据库

**原因：**
- AI 助手没有连接到数据源
- 数据源未激活或未选择

**解决方案：**
1. 确认数据源已添加并激活
2. 在 AI 助手设置中选择数据源
3. 检查数据源连接状态

### 问题：连接测试失败

**可能原因：**
- 使用了 `localhost` 而不是 `db`（Docker 网络问题）
- PostgreSQL 容器未运行
- 数据库不存在

**解决方案：**
```bash
# 检查容器状态
docker ps | grep postgres

# 检查数据库是否存在
docker exec dataagent-postgres psql -U postgres -l | grep chatbi_test

# 重新创建数据库（如果需要）
docker exec dataagent-postgres psql -U postgres -c "DROP DATABASE IF EXISTS chatbi_test;"
docker exec dataagent-postgres psql -U postgres -c "CREATE DATABASE chatbi_test;"
Get-Content scripts/init-chatbi-test-db-ascii.sql | docker exec -i dataagent-postgres psql -U postgres -d chatbi_test
```

---

## 📚 数据库连接信息

| 配置项 | 值 |
|--------|-----|
| **主机（容器内）** | `db` |
| **主机（宿主机）** | `localhost` |
| **端口** | `5432` |
| **数据库名** | `chatbi_test` |
| **用户名** | `postgres` |
| **密码** | `password` |
| **连接字符串（容器内）** | `postgresql://postgres:password@db:5432/chatbi_test` |
| **连接字符串（宿主机）** | `postgresql://postgres:password@localhost:5432/chatbi_test` |

---

## ✅ 验证清单

- [ ] PostgreSQL 容器正在运行
- [ ] chatbi_test 数据库已创建
- [ ] 数据已成功导入（7个表，共113条记录）
- [ ] 在 Data Agent 中添加了数据源
- [ ] 数据源连接测试成功
- [ ] 数据源状态为"激活"
- [ ] AI 助手可以查询数据并返回准确结果

---

**创建时间：** 2025-11-29
**数据库版本：** PostgreSQL 16
**测试数据年份：** 2024

