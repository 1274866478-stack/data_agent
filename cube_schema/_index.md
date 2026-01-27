# 数据库语义层 - 总索引

## 📊 可用语义层文档

| 文件名 | 业务域 | 关键度量 |
|-------|-------|---------|
| Orders.yaml | 订单 | total_revenue, order_count, unique_customers |
| Customers.yaml | 客户 | customer_count, total_revenue |
| Products.yaml | 商品 | product_count, total_inventory |
| Inventory.yaml | 库存 | stock_value, low_stock_count |

## 🔗 表关联关系

```
Orders (订单表)
  ├── customer_id → Customers.id (客户表)
  └── id → OrderItems.order_id (订单明细表，一对多)

Customers (客户表)
  └── id ← Orders.customer_id (订单表，多对一)

Products (商品表)
  └── id → Inventory.product_id (库存表，一对一)

Inventory (库存表)
  └── product_id → Products.id (商品表，多对一)
```

## 🎯 快速开始

### 1. 查看所有文档
```bash
# 调用工具
list_schema_files()

# 返回示例
[
  {"filename": "Orders.yaml", "size": 2048, "modified": "Mon Jan 26 10:00:00 2026"},
  {"filename": "Customers.yaml", "size": 1024, "modified": "Mon Jan 26 10:00:00 2026"},
  ...
]
```

### 2. 读取表结构
```bash
# 读取整个 Orders.yaml
read_schema_file("Orders.yaml")

# 只读取度量部分
read_schema_file("Orders.yaml", section="measures")

# 只读取维度部分
read_schema_file("Orders.yaml", section="dimensions")
```

### 3. 搜索关键词
```bash
# 搜索包含"收入"的所有度量
search_schema("revenue")

# 搜索特定字段
search_schema("customer_id")
```

## 📋 Orders.yaml 详细说明

### 度量 (Measures)
| 度量名 | 描述 | 类型 | SQL 表达式 |
|-------|------|------|----------|
| total_revenue | 订单总收入（包含折扣、税费和运费） | sum | total_amount |
| net_revenue | 订单净收入（总收入减去折扣） | sum | total_amount - discount_amount |
| order_count | 订单数量 | count | id |
| unique_customers | 唯一客户数量 | countDistinct | customer_id |

### 维度 (Dimensions)
| 维度名 | 描述 | 类型 |
|-------|------|------|
| order_date | 订单日期 | time |
| status | 订单状态 | string |
| created_at | 创建时间 | time |

## 📋 Customers.yaml 详细说明

### 度量 (Measures)
| 度量名 | 描述 | 类型 |
|-------|------|------|
| customer_count | 客户数量 | count |
| total_revenue | 客户总消费金额 | sum |

### 维度 (Dimensions)
| 维度名 | 描述 | 类型 |
|-------|------|------|
| email | 客户邮箱 | string |
| display_name | 客户名称 | string |
| created_at | 注册时间 | time |

## 📋 Products.yaml 详细说明

### 度量 (Measures)
| 度量名 | 描述 | 类型 |
|-------|------|------|
| product_count | 商品数量 | count |
| total_inventory | 总库存量 | sum |

### 维度 (Dimensions)
| 维度名 | 描述 | 类型 |
|-------|------|------|
| name | 商品名称 | string |
| category | 商品类别 | string |
| price | 商品价格 | number |

## 📋 Inventory.yaml 详细说明

### 度量 (Measures)
| 度量名 | 描述 | 类型 |
|-------|------|------|
| stock_value | 库存价值（库存数量 × 商品价格） | sum |
| low_stock_count | 低库存商品数量 | count |

### 维度 (Dimensions)
| 维度名 | 描述 | 类型 |
|-------|------|------|
| quantity | 库存数量 | number |
| reorder_point | 补货点 | number |
| last_restocked_at | 最后补货时间 | time |

## 🔄 常见业务指标计算

### 毛利率计算
```sql
SELECT
  SUM(net_revenue) as total_net_revenue,
  SUM(cost) as total_cost,
  (SUM(net_revenue) - SUM(cost)) / SUM(net_revenue) * 100 as gross_margin_percentage
FROM orders
JOIN order_items ON orders.id = order_items.order_id
```

### 库存周转率计算
```sql
SELECT
  SUM(quantity) as total_sold,
  AVG(stock_value) as avg_inventory_value,
  SUM(quantity) / AVG(stock_value) as inventory_turnover
FROM inventory
JOIN order_items ON inventory.product_id = order_items.product_id
```

### 客户生命周期价值 (CLV)
```sql
SELECT
  customer_id,
  COUNT(*) as total_orders,
  SUM(total_amount) as total_spent,
  SUM(total_amount) / COUNT(*) as avg_order_value
FROM orders
GROUP BY customer_id
ORDER BY total_spent DESC
```

## 🔒 安全规则

1. **多租户隔离**：所有查询自动注入 `tenant_id` 过滤器
2. **只读访问**：语义层文档仅供读取，不可修改
3. **路径验证**：严格的路径验证，防止路径遍历攻击
4. **内容截断**：单次读取限制 5000 字符，避免 Token 爆炸

## 📝 维护指南

### 更新语义层文档
1. 修改对应的 `.yaml` 文件
2. 更新本索引文件（`_index.md`）的相应部分
3. 运行测试验证工具调用正常

### 添加新表
1. 创建新的 `.yaml` 文件（如 `Categories.yaml`）
2. 在本文件中添加表说明和关联关系
3. 确保包含 measures、dimensions 和 sql_table 部分

---

**最后更新**: 2026-01-26
**维护者**: Data Agent Team
