# 电商数据分析可视化测试问题集

## 数据库概述

**数据库名**: `ecommerce_test_db`

**数据表结构**:
| 表名 | 说明 | 主要字段 |
|-----|------|---------|
| `users` | 用户表 | id, username, email, vip_level, total_spent, registration_date |
| `addresses` | 收货地址表 | id, user_id, province, city, district |
| `categories` | 商品类别表 | id, name, parent_id, description |
| `products` | 商品表 | id, name, category_id, price, stock, sales_count, rating, brand |
| `orders` | 订单表 | id, order_no, user_id, total_amount, final_amount, status, created_at |
| `order_items` | 订单明细表 | id, order_id, product_id, price, quantity, subtotal |
| `reviews` | 商品评价表 | id, order_id, product_id, user_id, rating, content, created_at |

---

## 测试问题清单

### 问题 1: 销售趋势分析
**问题描述**:
> 分析2024年1月到4月的月度销售趋势，统计每月的订单数量、总销售额和平均客单价，用折线图展示趋势变化。

**涉及表**: `orders`

**分析类型**: 时间序列分析

**推荐图表**: 折线图 (多Y轴)

**预期SQL要点**:
- 按 `DATE_TRUNC('month', created_at)` 分组
- 统计 `COUNT(*)`, `SUM(final_amount)`, `AVG(final_amount)`
- 筛选条件: `created_at >= '2024-01-01' AND status != 'cancelled'`

---

### 问题 2: 用户VIP等级分布
**问题描述**:
> 统计不同VIP等级用户的数量分布，以及各等级用户的平均消费金额，用饼图展示用户数量分布，柱状图对比平均消费。

**涉及表**: `users`

**分析类型**: 分组统计 + 对比分析

**推荐图表**: 饼图 + 柱状图

**预期SQL要点**:
- 按 `vip_level` 分组
- 统计 `COUNT(*)`, `AVG(total_spent)`
- 可选: 排序 `ORDER BY vip_level`

---

### 问题 3: 商品类别销售排行
**问题描述**:
> 按商品类别统计销售额和销量排行，分析哪个类别最受欢迎，用横向柱状图展示Top类别。

**涉及表**: `products`, `categories`, `order_items`

**分析类型**: 排行分析

**推荐图表**: 横向柱状图

**预期SQL要点**:
- JOIN: `order_items` → `products` → `categories`
- 按 `categories.name` 分组
- 统计 `SUM(subtotal)`, `SUM(quantity)`
- 排序: `ORDER BY SUM(subtotal) DESC`

---

### 问题 4: 商品价格与销量关系分析
**问题描述**:
> 分析商品价格与销量的关系，找出高销量低价和高价低销的商品，用散点图展示价格vs销量分布。

**涉及表**: `products`

**分析类型**: 关联分析

**推荐图表**: 散点图

**预期SQL要点**:
- 选择: `name`, `price`, `sales_count`
- 可选: 添加类别、品牌作为颜色分组维度
- 筛选: `is_on_sale = true AND stock > 0`

---

### 问题 5: 地区销售分布
**问题描述**:
> 按用户收货地址的省份统计销售分布，展示各省份的订单数量和销售额，用地图或柱状图展示。

**涉及表**: `users`, `addresses`, `orders`

**分析类型**: 地理分布分析

**推荐图表**: 地图 / 柱状图

**预期SQL要点**:
- JOIN: `orders` → `addresses`
- 按 `province` 分组
- 统计 `COUNT(*)`, `SUM(final_amount)`
- 筛选: `status != 'cancelled'`

---

### 问题 6: 订单状态转化漏斗
**问题描述**:
> 分析订单从待付款到完成的状态流转情况，统计各状态订单数量，用漏斗图展示订单转化率。

**涉及表**: `orders`

**分析类型**: 漏斗分析

**推荐图表**: 漏斗图

**预期SQL要点**:
- 按 `status` 分组
- 统计 `COUNT(*)`
- 状态顺序: pending → paid → shipped → completed (排除 cancelled)

---

### 问题 7: 商品评分与销量关联分析
**问题描述**:
> 分析商品评分与销量的关系，用散点图展示评分vs销量，并标注高评分高销量的明星产品。

**涉及表**: `products`, `reviews`

**分析类型**: 关联分析

**推荐图表**: 散点图 (带标注)

**预期SQL要点**:
- JOIN: `products` + `reviews` (或直接使用 `products.rating`)
- 选择: `name`, `rating`, `sales_count`
- 筛选条件: `review_count > 0` (有评价的商品)

---

### 问题 8: 用户复购行为分析
**问题描述**:
> 统计每个用户的下单次数，分析复购用户占比，用直方图展示用户订单数量分布。

**涉及表**: `orders`

**分析类型**: 用户行为分析

**推荐图表**: 直方图

**预期SQL要点**:
- 按 `user_id` 分组，统计 `COUNT(*)`
- 再对订单数进行分组统计频次
- 计算复购率: 下单次数 > 1 的用户占比

---

### 问题 9: 品牌市场份额分析
**问题描述**:
> 按品牌统计商品销售额和销量，计算各品牌的市场份额，用饼图或环形图展示品牌占比。

**涉及表**: `products`, `order_items`

**分析类型**: 市场份额分析

**推荐图表**: 饼图 / 环形图

**预期SQL要点**:
- JOIN: `order_items` → `products`
- 按 `brand` 分组
- 统计 `SUM(subtotal)`, `SUM(quantity)`
- 计算百分比: `SUM(subtotal) / 总销售额 * 100`

---

### 问题 10: 评价满意度趋势
**问题描述**:
> 分析每月商品评价的平均评分变化趋势，同时展示评价数量，用双轴图（折线+柱状）展示评分和评价数量的关系。

**涉及表**: `reviews`, `orders`

**分析类型**: 时间序列 + 双轴分析

**推荐图表**: 双轴图 (折线 + 柱状)

**预期SQL要点**:
- 按 `DATE_TRUNC('month', reviews.created_at)` 分组
- 统计 `AVG(rating)`, `COUNT(*)`
- 可选: JOIN `orders` 获取订单状态过滤

---

## 问题-表映射关系总览

| 问题ID | 问题描述 | 涉及表 | 分析类型 | 推荐图表 |
|--------|---------|-------|---------|---------|
| 1 | 销售趋势分析 | orders | 时间序列 | 折线图 |
| 2 | VIP等级分布 | users | 分组统计 | 饼图+柱状图 |
| 3 | 类别销售排行 | products, categories, order_items | 排行分析 | 横向柱状图 |
| 4 | 价格-销量关系 | products | 关联分析 | 散点图 |
| 5 | 地区销售分布 | users, addresses, orders | 地理分析 | 地图/柱状图 |
| 6 | 订单转化漏斗 | orders | 漏斗分析 | 漏斗图 |
| 7 | 评分-销量关联 | products, reviews | 关联分析 | 散点图 |
| 8 | 用户复购行为 | orders | 用户行为 | 直方图 |
| 9 | 品牌市场份额 | products, order_items | 市场分析 | 饼图/环形图 |
| 10 | 满意度趋势 | reviews, orders | 时间序列 | 双轴图 |

---

## 测试覆盖维度

### 业务场景覆盖
- [x] 销售分析 (Q1, Q3, Q9)
- [x] 用户分析 (Q2, Q8)
- [x] 商品分析 (Q4, Q7)
- [x] 地理分析 (Q5)
- [x] 流程分析 (Q6)
- [x] 满意度分析 (Q10)

### 技术能力覆盖
- [x] 单表查询 (Q2, Q4, Q6, Q8)
- [x] 多表JOIN (Q3, Q5, Q7, Q9, Q10)
- [x] 时间分组聚合 (Q1, Q10)
- [x] 分组统计 (Q2, Q3, Q5, Q6, Q8, Q9)
- [x] 子查询/嵌套 (Q8)

### 图表类型覆盖
- [x] 折线图
- [x] 柱状图
- [x] 横向柱状图
- [x] 饼图/环形图
- [x] 散点图
- [x] 直方图
- [x] 漏斗图
- [x] 双轴图
- [x] 地图

---

## 使用说明

### 执行测试
1. 确保电商测试数据库已初始化
2. 在AI助手中依次输入上述问题
3. 验证生成的SQL是否正确
4. 检查可视化图表是否符合预期
5. 记录问题和改进建议

### 评分标准
| 维度 | 权重 | 说明 |
|-----|------|-----|
| SQL正确性 | 40% | SQL语法正确，结果准确 |
| 图表适配性 | 30% | 图表类型选择合理，展示清晰 |
| 分析深度 | 20% | 包含洞察和业务解读 |
| 响应速度 | 10% | 查询和渲染效率 |

---

*文档生成时间: 2026-01-29*
*数据版本: ecommerce_test_db v1.0*
