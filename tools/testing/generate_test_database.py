"""
生成Excel测试数据库

创建一个包含多张关联表的Excel文件，用于测试数据源连接和SQL查询功能。

表结构：
1. regions (区域表) - 销售区域
2. customers (客户表) - 客户信息
3. categories (产品分类表) - 产品分类
4. products (产品表) - 产品信息
5. orders (订单表) - 订单主表
6. order_items (订单明细表) - 订单明细
7. employees (员工表) - 员工信息
8. suppliers (供应商表) - 供应商信息
9. inventory (库存表) - 库存信息
10. sales_targets (销售目标表) - 销售目标
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 设置随机种子确保可复现
np.random.seed(42)

# ===== 1. 区域表 (regions) =====
regions_data = {
    'region_id': [1, 2, 3, 4, 5],
    'region_name': ['华东区', '华北区', '华南区', '西南区', '西北区'],
    'country': ['中国', '中国', '中国', '中国', '中国'],
    'manager_name': ['张明', '李华', '王芳', '赵强', '刘洋']
}
regions_df = pd.DataFrame(regions_data)

# ===== 2. 客户表 (customers) =====
first_names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '洋', '勇', '军', '杰', '娟', '涛', '明']
last_names = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '胡', '郭']

customers = []
for i in range(1, 201):
    customer = {
        'customer_id': i,
        'customer_name': f"{np.random.choice(last_names)}{np.random.choice(first_names)}",
        'region_id': np.random.choice([1, 2, 3, 4, 5]),
        'email': f"customer{i}@example.com",
        'phone': f"1{np.random.randint(3, 10)}{np.random.randint(100000000, 999999999)}",
        'address': f"{np.random.choice(['北京市', '上海市', '广州市', '深圳市', '杭州市', '成都市', '西安市', '南京市'])}{np.random.choice(['朝阳区', '浦东新区', '天河区', '福田区', '西湖区', '高新区'])}{np.random.randint(1, 999)}号",
        'credit_level': np.random.choice(['A', 'B', 'C', 'D']),
        'registered_date': datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 600)),
        'total_orders': np.random.randint(0, 100),
        'total_spent': round(np.random.uniform(0, 500000), 2),
        'status': np.random.choice(['active', 'inactive', 'suspended'], p=[0.85, 0.12, 0.03])
    }
    customers.append(customer)
customers_df = pd.DataFrame(customers)

# ===== 3. 产品分类表 (categories) =====
categories_data = {
    'category_id': [1, 2, 3, 4, 5, 6, 7, 8],
    'category_name': ['电子产品', '家居用品', '服装鞋帽', '食品饮料', '图书文具', '运动户外', '美妆护肤', '母婴用品'],
    'description': [
        '手机、电脑、数码配件等电子产品',
        '家具、家纺、厨具等家居用品',
        '男装、女装、童装、鞋类等',
        '零食、饮料、生鲜食品等',
        '图书、办公用品、文具等',
        '运动器材、户外装备等',
        '护肤品、化妆品等',
        '奶粉、尿裤、玩具等'
    ]
}
categories_df = pd.DataFrame(categories_data)

# ===== 4. 产品表 (products) =====
product_templates = [
    {'category_id': 1, 'names': ['iPhone 15 Pro', '小米14 Pro', 'MacBook Air M3', '华为MateBook X Pro', 'AirPods Pro 2', '索尼WH-1000XM5', '戴尔XPS 15', 'iPad Air 5', '华为Mate 60', '三星Galaxy S24'], 'price_range': (500, 15000)},
    {'category_id': 2, 'names': ['真皮沙发', '实木餐桌', '记忆棉床垫', '智能扫地机器人', '空气净化器', '电饭煲', '破壁机', '空气净化器', '全自动洗衣机', '双门冰箱'], 'price_range': (200, 8000)},
    {'category_id': 3, 'names': ['男士商务衬衫', '女士连衣裙', '运动休闲裤', '休闲运动鞋', '牛仔外套', '羽绒服', '真丝围巾', '皮带', '棒球帽', '棉质T恤'], 'price_range': (50, 1500)},
    {'category_id': 4, 'names': ['进口牛奶', '有机坚果', '进口红酒', '高档茶叶', '进口巧克力', '橄榄油', '婴幼儿奶粉', '进口饼干', '新鲜水果', '有机大米'], 'price_range': (30, 800)},
    {'category_id': 5, 'names': ['Python编程入门', '深度学习', '经济学原理', '设计心理学', '三体全集', '哈利波特全集', '办公文具套装', '笔记本', '钢笔礼盒', '签字笔套装'], 'price_range': (15, 200)},
    {'category_id': 6, 'names': ['瑜伽垫', '跑步机', '健身哑铃套装', '登山背包', '户外帐篷', '乒乓球拍', '篮球', '足球', '游泳镜', '运动手环'], 'price_range': (50, 3000)},
    {'category_id': 7, 'names': ['保湿面霜', '精华液', '口红套装', '防晒霜', '洗面奶', '面膜套装', '香水', '化妆刷套装', '眼霜', '身体乳'], 'price_range': (80, 2000)},
    {'category_id': 8, 'names': ['婴儿纸尿裤', '婴儿配方奶粉', '儿童安全座椅', '婴儿推车', '婴儿湿巾', '儿童玩具套装', '婴儿衣服', '奶瓶消毒器', '婴儿监护器', '儿童餐椅'], 'price_range': (50, 2500)},
]

products = []
product_id = 1
for template in product_templates:
    for name in template['names']:
        base_price = np.random.uniform(*template['price_range'])
        for _ in range(np.random.randint(1, 4)):  # 每个产品可能有1-3个变体
            products.append({
                'product_id': product_id,
                'product_name': name,
                'category_id': template['category_id'],
                'unit_price': round(base_price * np.random.uniform(0.9, 1.1), 2),
                'cost_price': round(base_price * np.random.uniform(0.5, 0.7), 2),
                'stock_quantity': np.random.randint(0, 500),
                'reorder_level': np.random.randint(10, 50),
                'discontinued': np.random.choice([0, 1], p=[0.95, 0.05]),
                'supplier_id': np.random.randint(1, 20)
            })
            product_id += 1
products_df = pd.DataFrame(products)

# ===== 5. 员工表 (employees) =====
employees = []
positions = ['销售经理', '销售代表', '客服专员', '仓库管理员', '物流专员', '财务专员', '产品经理']
departments = ['销售部', '客服部', '仓储部', '物流部', '财务部', '产品部']
for i in range(1, 51):
    hire_date = datetime(2020, 1, 1) + timedelta(days=np.random.randint(0, 1500))
    employees.append({
        'employee_id': i,
        'employee_name': f"{np.random.choice(last_names)}{np.random.choice(first_names)}",
        'position': np.random.choice(positions),
        'department': np.random.choice(departments),
        'region_id': np.random.choice([1, 2, 3, 4, 5]),
        'hire_date': hire_date,
        'salary': round(np.random.uniform(5000, 25000), 2),
        'email': f"employee{i}@company.com",
        'phone': f"1{np.random.randint(3, 10)}{np.random.randint(100000000, 999999999)}",
        'status': np.random.choice(['active', 'on_leave', 'resigned'], p=[0.90, 0.05, 0.05])
    })
employees_df = pd.DataFrame(employees)

# ===== 6. 供应商表 (suppliers) =====
suppliers = []
supplier_suffixes = ['科技', '贸易', '实业', '电子', '商贸', '制造', '集团', '有限']
supplier_types = ['制造商', '批发商', '分销商', '进口商']
cities = ['深圳', '广州', '上海', '北京', '杭州', '苏州', '成都', '武汉', '西安', '南京']
for i in range(1, 31):
    suppliers.append({
        'supplier_id': i,
        'supplier_name': f"{np.random.choice(cities)}{np.random.choice(last_names)}氏{np.random.choice(supplier_suffixes)}公司",
        'contact_person': f"{np.random.choice(last_names)}{np.random.choice(first_names)}",
        'phone': f"0{np.random.randint(10, 30)}-{np.random.randint(10000000, 99999999)}",
        'email': f"contact@supplier{i}.com",
        'address': f"{np.random.choice(cities)}市{np.random.choice(['高新区', '开发区', '工业区'])}{np.random.randint(1, 888)}号",
        'supplier_type': np.random.choice(supplier_types),
        'credit_rating': np.random.choice(['AAA', 'AA', 'A', 'BBB'], p=[0.15, 0.35, 0.35, 0.15]),
        'status': np.random.choice(['active', 'inactive'], p=[0.9, 0.1])
    })
suppliers_df = pd.DataFrame(suppliers)

# ===== 7. 订单表 (orders) =====
orders = []
order_id = 1
for customer_id in range(1, 201):
    # 每个客户有0-50个订单
    num_orders = np.random.randint(0, 51)
    for _ in range(num_orders):
        order_date = datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 600))
        required_date = order_date + timedelta(days=np.random.randint(1, 30))
        shipped_date = order_date + timedelta(days=np.random.randint(0, 10)) if np.random.random() > 0.15 else None

        orders.append({
            'order_id': order_id,
            'customer_id': customer_id,
            'employee_id': np.random.randint(1, 51),
            'order_date': order_date,
            'required_date': required_date,
            'shipped_date': shipped_date,
            'shipper_id': np.random.randint(1, 6),
            'freight': round(np.random.uniform(0, 500), 2),
            'ship_name': f"{np.random.choice(last_names)}{np.random.choice(first_names)}",
            'ship_address': f"{np.random.choice(['北京', '上海', '广州', '深圳', '杭州'])}{np.random.randint(1, 999)}号",
            'ship_city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州']),
            'ship_postal_code': f"{np.random.randint(100000, 999999)}",
            'ship_country': '中国',
            'status': np.random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled'], p=[0.1, 0.2, 0.3, 0.35, 0.05])
        })
        order_id += 1
orders_df = pd.DataFrame(orders)

# ===== 8. 订单明细表 (order_items) =====
order_items = []
item_id = 1
for order_id in orders_df['order_id']:
    # 每个订单有1-10个明细项
    num_items = np.random.randint(1, 11)
    for _ in range(num_items):
        product = products_df.iloc[np.random.randint(0, len(products_df))]
        quantity = np.random.randint(1, 11)
        unit_price = product['unit_price'] * np.random.uniform(0.9, 1.1)  # 可能有价格波动
        discount = np.random.uniform(0, 0.3)  # 0-30%折扣

        order_items.append({
            'item_id': item_id,
            'order_id': order_id,
            'product_id': product['product_id'],
            'unit_price': round(unit_price, 2),
            'quantity': quantity,
            'discount': round(discount, 4)
        })
        item_id += 1
order_items_df = pd.DataFrame(order_items)

# ===== 9. 库存表 (inventory) =====
inventory = []
warehouses = ['北京仓', '上海仓', '广州仓', '深圳仓', '成都仓']
for idx, product in products_df.iterrows():
    inventory.append({
        'inventory_id': product['product_id'],
        'product_id': product['product_id'],
        'warehouse': np.random.choice(warehouses),
        'quantity': np.random.randint(0, 1000),
        'last_restock_date': datetime(2024, 1, 1) + timedelta(days=np.random.randint(0, 300)),
        'reorder_point': np.random.randint(20, 100),
        'reorder_quantity': np.random.randint(50, 500)
    })
inventory_df = pd.DataFrame(inventory)

# ===== 10. 销售目标表 (sales_targets) =====
sales_targets = []
target_id = 1
for year in [2023, 2024, 2025]:
    for quarter in [1, 2, 3, 4]:
        for region_id in [1, 2, 3, 4, 5]:
            sales_targets.append({
                'target_id': target_id,
                'region_id': region_id,
                'year': year,
                'quarter': quarter,
                'revenue_target': round(np.random.uniform(500000, 2000000), 2),
                'order_count_target': np.random.randint(100, 1001),
                'new_customer_target': np.random.randint(10, 101),
                'achieved': np.random.choice([0, 1], p=[0.3, 0.7]) if year < 2025 else 0
            })
            target_id += 1
sales_targets_df = pd.DataFrame(sales_targets)

# ===== 创建Excel文件 =====
output_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(output_dir, 'test_database.xlsx')

print(f"正在生成Excel测试数据库: {output_file}")
print("=" * 60)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 写入所有表
    regions_df.to_excel(writer, sheet_name='regions', index=False)
    customers_df.to_excel(writer, sheet_name='customers', index=False)
    categories_df.to_excel(writer, sheet_name='categories', index=False)
    products_df.to_excel(writer, sheet_name='products', index=False)
    employees_df.to_excel(writer, sheet_name='employees', index=False)
    suppliers_df.to_excel(writer, sheet_name='suppliers', index=False)
    orders_df.to_excel(writer, sheet_name='orders', index=False)
    order_items_df.to_excel(writer, sheet_name='order_items', index=False)
    inventory_df.to_excel(writer, sheet_name='inventory', index=False)
    sales_targets_df.to_excel(writer, sheet_name='sales_targets', index=False)

    # 调整列宽
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

# ===== 打印统计信息 =====
print("\nExcel测试数据库生成完成！")
print("=" * 60)
print(f"文件位置: {output_file}")
print("\n表统计信息:")
print(f"  regions         区域表: {len(regions_df)} 行")
print(f"  customers       客户表: {len(customers_df)} 行")
print(f"  categories      分类表: {len(categories_df)} 行")
print(f"  products        产品表: {len(products_df)} 行")
print(f"  employees       员工表: {len(employees_df)} 行")
print(f"  suppliers      供应商表: {len(suppliers_df)} 行")
print(f"  orders          订单表: {len(orders_df)} 行")
print(f"  order_items   订单明细表: {len(order_items_df)} 行")
print(f"  inventory        库存表: {len(inventory_df)} 行")
print(f"  sales_targets 销售目标表: {len(sales_targets_df)} 行")
print("\n总计 10 张表")
print("=" * 60)

print("\n支持的测试场景:")
print("  ✓ 基础查询: SELECT, WHERE, ORDER BY, LIMIT")
print("  ✓ 聚合查询: COUNT, SUM, AVG, MAX, MIN")
print("  ✓ 分组统计: GROUP BY, HAVING")
print("  ✓ 连接查询: INNER JOIN, LEFT JOIN")
print("  ✓ 子查询: EXISTS, IN, 关联子查询")
print("  ✓ 窗口函数: ROW_NUMBER, RANK, DENSE_RANK")
print("  ✓ 日期操作: 时间范围查询、日期计算")
print("  ✓ 字符串操作: LIKE, SUBSTRING, CONCAT")
print("  ✓ 条件逻辑: CASE WHEN")
print("=" * 60)

print("\n示例查询:")
print("-- 1. 查询每个客户的订单总金额")
print("SELECT c.customer_name, COUNT(o.order_id) as order_count,")
print("       SUM(oi.unit_price * oi.quantity * (1 - oi.discount)) as total_spent")
print("FROM customers c")
print("LEFT JOIN orders o ON c.customer_id = o.customer_id")
print("LEFT JOIN order_items oi ON o.order_id = oi.order_id")
print("GROUP BY c.customer_id, c.customer_name")
print("ORDER BY total_spent DESC")
print("LIMIT 10;")
print()
print("-- 2. 查询每个区域的销售排名")
print("SELECT r.region_name, e.employee_name,")
print("       COUNT(o.order_id) as order_count,")
print("       RANK() OVER (PARTITION BY r.region_id ORDER BY COUNT(o.order_id) DESC) as sales_rank")
print("FROM regions r")
print("JOIN employees e ON r.region_id = e.region_id")
print("LEFT JOIN orders o ON e.employee_id = o.employee_id")
print("GROUP BY r.region_id, r.region_name, e.employee_id, e.employee_name")
print("ORDER BY r.region_id, sales_rank;")
print()
print("-- 3. 查询库存不足的产品")
print("SELECT p.product_name, p.stock_quantity, p.reorder_level, c.category_name")
print("FROM products p")
print("JOIN categories c ON p.category_id = c.category_id")
print("WHERE p.stock_quantity < p.reorder_level")
print("ORDER BY p.stock_quantity ASC;")
print("=" * 60)
