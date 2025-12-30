#!/usr/bin/env python3
"""
生成两个相关联的测试数据库
用于测试跨数据源查询功能

数据库1: 销售订单数据库 (sales_orders.xlsx)
  - 订单表: 订单基本信息
  - 订单明细表: 订单商品详情
  - 商品表: 商品信息

数据库2: 客户管理数据库 (customer_management.xlsx)
  - 客户表: 客户基本信息
  - 地址表: 客户收货地址
  - 会员积分表: 积分记录

两个数据库通过 客户ID 关联，可以测试:
  1. 跨数据源JOIN查询
  2. 关联统计分析
  3. 多表数据聚合
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# 设置随机种子保证可重复性
np.random.seed(42)
random.seed(42)

# ==================== 基础数据定义 ====================

# 中文姓名生成
SURNAMES = ['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '高', '罗']
MALE_NAMES = ['伟', '强', '磊', '军', '杰', '勇', '涛', '明', '超', '刚', '平', '辉', '鹏', '斌', '华', '亮', '建', '峰', '浩', '宇']
FEMALE_NAMES = ['芳', '娟', '敏', '静', '丽', '艳', '娜', '秀英', '玲', '燕', '红', '慧', '婷', '雪', '萍', '梅', '霞', '倩', '琴', '蕾']

# 城市和地区
CITIES = {
    '北京市': ['朝阳区', '海淀区', '东城区', '西城区', '丰台区'],
    '上海市': ['浦东新区', '徐汇区', '静安区', '黄浦区', '杨浦区'],
    '广州市': ['天河区', '越秀区', '海珠区', '白云区', '番禺区'],
    '深圳市': ['福田区', '南山区', '罗湖区', '宝安区', '龙岗区'],
    '杭州市': ['西湖区', '上城区', '拱墅区', '滨江区', '余杭区'],
}

# 商品信息
PRODUCTS = [
    {'id': 'P001', 'name': '无线蓝牙耳机', 'category': '数码配件', 'price': 299.00, 'cost': 150.00},
    {'id': 'P002', 'name': '智能手表', 'category': '智能穿戴', 'price': 899.00, 'cost': 450.00},
    {'id': 'P003', 'name': '便携充电宝', 'category': '数码配件', 'price': 159.00, 'cost': 80.00},
    {'id': 'P004', 'name': '机械键盘', 'category': '电脑配件', 'price': 399.00, 'cost': 200.00},
    {'id': 'P005', 'name': '无线鼠标', 'category': '电脑配件', 'price': 199.00, 'cost': 100.00},
    {'id': 'P006', 'name': '平板电脑支架', 'category': '数码配件', 'price': 89.00, 'cost': 35.00},
    {'id': 'P007', 'name': '运动水杯', 'category': '生活用品', 'price': 69.00, 'cost': 25.00},
    {'id': 'P008', 'name': '护眼台灯', 'category': '家居用品', 'price': 259.00, 'cost': 130.00},
    {'id': 'P009', 'name': '保温杯', 'category': '生活用品', 'price': 129.00, 'cost': 50.00},
    {'id': 'P010', 'name': '笔记本电脑包', 'category': '箱包', 'price': 179.00, 'cost': 70.00},
    {'id': 'P011', 'name': '手机壳', 'category': '手机配件', 'price': 49.00, 'cost': 15.00},
    {'id': 'P012', 'name': '数据线套装', 'category': '数码配件', 'price': 39.00, 'cost': 12.00},
    {'id': 'P013', 'name': '迷你风扇', 'category': '小家电', 'price': 79.00, 'cost': 30.00},
    {'id': 'P014', 'name': '颈部按摩仪', 'category': '健康电器', 'price': 399.00, 'cost': 180.00},
    {'id': 'P015', 'name': '加湿器', 'category': '小家电', 'price': 189.00, 'cost': 80.00},
]

# 会员等级
VIP_LEVELS = ['普通会员', '银卡会员', '金卡会员', '钻石会员']
VIP_DISCOUNT = {'普通会员': 1.0, '银卡会员': 0.95, '金卡会员': 0.90, '钻石会员': 0.85}

# 订单状态
ORDER_STATUS = ['待付款', '已付款', '已发货', '已完成', '已取消', '退款中']
ORDER_STATUS_WEIGHTS = [0.05, 0.10, 0.15, 0.60, 0.05, 0.05]

# 支付方式
PAYMENT_METHODS = ['微信支付', '支付宝', '银行卡', '花呗', '信用卡']


def generate_name(gender):
    """生成中文姓名"""
    surname = random.choice(SURNAMES)
    if gender == '男':
        name = random.choice(MALE_NAMES)
    else:
        name = random.choice(FEMALE_NAMES)
    return surname + name


def generate_phone():
    """生成手机号"""
    prefixes = ['130', '131', '135', '136', '138', '139', '150', '151', '155', '158', '180', '182', '188']
    return random.choice(prefixes) + ''.join([str(random.randint(0, 9)) for _ in range(8)])


def generate_email(name_pinyin, index):
    """生成邮箱"""
    domains = ['qq.com', '163.com', 'gmail.com', 'outlook.com', 'sina.com']
    return f"user{index}@{random.choice(domains)}"


# ==================== 客户管理数据库 (customer_management.xlsx) ====================

def generate_customers(n=50):
    """生成客户数据"""
    customers = []
    for i in range(1, n + 1):
        gender = random.choice(['男', '女'])
        age = random.randint(18, 65)
        reg_date = datetime.now() - timedelta(days=random.randint(30, 730))
        
        # VIP等级与消费金额相关
        vip_level = np.random.choice(VIP_LEVELS, p=[0.40, 0.30, 0.20, 0.10])
        
        customers.append({
            '客户ID': f'C{str(i).zfill(4)}',
            '客户姓名': generate_name(gender),
            '性别': gender,
            '年龄': age,
            '手机号': generate_phone(),
            '邮箱': generate_email('user', i),
            '会员等级': vip_level,
            '注册日期': reg_date.strftime('%Y-%m-%d'),
            '最后登录': (reg_date + timedelta(days=random.randint(1, (datetime.now() - reg_date).days or 1))).strftime('%Y-%m-%d'),
            '账户状态': np.random.choice(['正常', '冻结', '注销'], p=[0.92, 0.05, 0.03]),
        })
    return pd.DataFrame(customers)


def generate_addresses(customers_df):
    """生成地址数据 - 每个客户1-3个地址"""
    addresses = []
    addr_id = 1
    
    for _, customer in customers_df.iterrows():
        # 每个客户1-3个地址
        addr_count = random.randint(1, 3)
        for j in range(addr_count):
            city = random.choice(list(CITIES.keys()))
            district = random.choice(CITIES[city])
            
            addresses.append({
                '地址ID': f'A{str(addr_id).zfill(4)}',
                '客户ID': customer['客户ID'],
                '收货人': customer['客户姓名'] if j == 0 else generate_name(random.choice(['男', '女'])),
                '联系电话': customer['手机号'] if j == 0 else generate_phone(),
                '省份': city.replace('市', '') if '市' in city else city,
                '城市': city,
                '区县': district,
                '详细地址': f"{random.choice(['幸福路', '和平街', '建设大道', '科技路', '文化路'])}{random.randint(1, 200)}号{random.randint(1, 30)}栋{random.randint(1, 4)}单元{random.randint(101, 2505)}室",
                '是否默认': '是' if j == 0 else '否',
                '地址类型': random.choice(['家', '公司', '其他']),
            })
            addr_id += 1
    
    return pd.DataFrame(addresses)


def generate_points_records(customers_df, n=200):
    """生成会员积分记录"""
    records = []
    customer_ids = customers_df['客户ID'].tolist()
    
    for i in range(1, n + 1):
        customer_id = random.choice(customer_ids)
        record_type = random.choice(['消费获取', '签到获取', '活动奖励', '积分兑换', '过期扣除'])
        
        if record_type in ['消费获取', '签到获取', '活动奖励']:
            points = random.randint(10, 500)
        else:
            points = -random.randint(50, 300)
        
        record_date = datetime.now() - timedelta(days=random.randint(0, 365))
        
        records.append({
            '记录ID': f'PR{str(i).zfill(5)}',
            '客户ID': customer_id,
            '积分变动': points,
            '变动类型': record_type,
            '变动描述': f"{'获取' if points > 0 else '扣除'}积分{abs(points)}分",
            '关联订单': f"ORD{str(random.randint(1, 150)).zfill(5)}" if record_type == '消费获取' else '',
            '变动时间': record_date.strftime('%Y-%m-%d %H:%M:%S'),
            '操作人': '系统' if record_type != '积分兑换' else '用户',
        })
    
    return pd.DataFrame(records)


# ==================== 销售订单数据库 (sales_orders.xlsx) ====================

def generate_products_df():
    """生成商品数据"""
    products = []
    for p in PRODUCTS:
        products.append({
            '商品ID': p['id'],
            '商品名称': p['name'],
            '商品分类': p['category'],
            '销售价格': p['price'],
            '成本价格': p['cost'],
            '库存数量': random.randint(50, 500),
            '销量': random.randint(10, 300),
            '评分': round(random.uniform(4.0, 5.0), 1),
            '上架状态': np.random.choice(['在售', '下架', '预售'], p=[0.85, 0.10, 0.05]),
            '供应商': random.choice(['供应商A', '供应商B', '供应商C', '供应商D']),
            '创建时间': (datetime.now() - timedelta(days=random.randint(100, 500))).strftime('%Y-%m-%d'),
        })
    return pd.DataFrame(products)


def generate_orders(customers_df, n=150):
    """生成订单数据"""
    orders = []
    customer_ids = customers_df['客户ID'].tolist()
    
    for i in range(1, n + 1):
        customer_id = random.choice(customer_ids)
        customer = customers_df[customers_df['客户ID'] == customer_id].iloc[0]
        
        order_date = datetime.now() - timedelta(days=random.randint(0, 365))
        status = np.random.choice(ORDER_STATUS, p=ORDER_STATUS_WEIGHTS)
        
        # 根据状态设置时间
        if status in ['已付款', '已发货', '已完成']:
            pay_time = order_date + timedelta(minutes=random.randint(5, 60))
        else:
            pay_time = None
            
        if status in ['已发货', '已完成']:
            ship_time = pay_time + timedelta(hours=random.randint(12, 72)) if pay_time else None
        else:
            ship_time = None
            
        if status == '已完成':
            complete_time = ship_time + timedelta(days=random.randint(1, 7)) if ship_time else None
        else:
            complete_time = None
        
        # 计算金额（后面会根据订单明细更新）
        total = round(random.uniform(100, 2000), 2)
        discount = round(total * (1 - VIP_DISCOUNT.get(customer['会员等级'], 1.0)), 2)
        shipping = 0 if total > 99 else 10
        
        orders.append({
            '订单ID': f'ORD{str(i).zfill(5)}',
            '客户ID': customer_id,
            '订单日期': order_date.strftime('%Y-%m-%d'),
            '订单时间': order_date.strftime('%H:%M:%S'),
            '订单状态': status,
            '商品总额': total,
            '优惠金额': discount,
            '运费': shipping,
            '实付金额': round(total - discount + shipping, 2),
            '支付方式': random.choice(PAYMENT_METHODS) if pay_time else '',
            '付款时间': pay_time.strftime('%Y-%m-%d %H:%M:%S') if pay_time else '',
            '发货时间': ship_time.strftime('%Y-%m-%d %H:%M:%S') if ship_time else '',
            '完成时间': complete_time.strftime('%Y-%m-%d %H:%M:%S') if complete_time else '',
            '订单备注': random.choice(['', '', '', '请尽快发货', '周末配送', '放门卫处']),
        })
    
    return pd.DataFrame(orders)


def generate_order_items(orders_df):
    """生成订单明细"""
    items = []
    item_id = 1
    
    for _, order in orders_df.iterrows():
        # 每个订单1-4个商品
        item_count = random.randint(1, 4)
        selected_products = random.sample(PRODUCTS, item_count)
        
        order_total = 0
        for product in selected_products:
            quantity = random.randint(1, 3)
            unit_price = product['price']
            subtotal = round(unit_price * quantity, 2)
            order_total += subtotal
            
            items.append({
                '明细ID': f'OI{str(item_id).zfill(5)}',
                '订单ID': order['订单ID'],
                '商品ID': product['id'],
                '商品名称': product['name'],
                '商品分类': product['category'],
                '单价': unit_price,
                '数量': quantity,
                '小计': subtotal,
                '是否评价': np.random.choice(['是', '否'], p=[0.7, 0.3]) if order['订单状态'] == '已完成' else '否',
            })
            item_id += 1
    
    return pd.DataFrame(items)


def update_order_totals(orders_df, order_items_df, customers_df):
    """根据订单明细更新订单金额"""
    for idx, order in orders_df.iterrows():
        items = order_items_df[order_items_df['订单ID'] == order['订单ID']]
        total = items['小计'].sum()
        
        customer = customers_df[customers_df['客户ID'] == order['客户ID']].iloc[0]
        discount_rate = 1 - VIP_DISCOUNT.get(customer['会员等级'], 1.0)
        discount = round(total * discount_rate, 2)
        shipping = 0 if total > 99 else 10
        
        orders_df.at[idx, '商品总额'] = round(total, 2)
        orders_df.at[idx, '优惠金额'] = discount
        orders_df.at[idx, '运费'] = shipping
        orders_df.at[idx, '实付金额'] = round(total - discount + shipping, 2)
    
    return orders_df


def main():
    """主函数：生成两个相关联的测试数据库"""
    print("=" * 60)
    print("开始生成两个相关联的测试数据库...")
    print("=" * 60)
    
    # ========== 数据库1: 客户管理数据库 ==========
    print("\n[数据库1] 生成客户管理数据库 (customer_management.xlsx)...")
    
    print("  [1/3] 生成客户数据...")
    customers_df = generate_customers(50)
    
    print("  [2/3] 生成地址数据...")
    addresses_df = generate_addresses(customers_df)
    
    print("  [3/3] 生成积分记录...")
    points_df = generate_points_records(customers_df, 200)
    
    # 保存客户管理数据库
    customer_db_path = os.path.join(os.path.dirname(__file__), 'customer_management.xlsx')
    with pd.ExcelWriter(customer_db_path, engine='openpyxl') as writer:
        customers_df.to_excel(writer, sheet_name='客户信息', index=False)
        addresses_df.to_excel(writer, sheet_name='收货地址', index=False)
        points_df.to_excel(writer, sheet_name='积分记录', index=False)
    
    print(f"  [OK] 已保存: {customer_db_path}")
    
    # ========== 数据库2: 销售订单数据库 ==========
    print("\n[数据库2] 生成销售订单数据库 (sales_orders.xlsx)...")
    
    print("  [1/3] 生成商品数据...")
    products_df = generate_products_df()
    
    print("  [2/3] 生成订单数据...")
    orders_df = generate_orders(customers_df, 150)
    
    print("  [3/3] 生成订单明细...")
    order_items_df = generate_order_items(orders_df)
    
    # 更新订单金额
    print("  [更新] 计算订单金额...")
    orders_df = update_order_totals(orders_df, order_items_df, customers_df)
    
    # 保存销售订单数据库
    sales_db_path = os.path.join(os.path.dirname(__file__), 'sales_orders.xlsx')
    with pd.ExcelWriter(sales_db_path, engine='openpyxl') as writer:
        products_df.to_excel(writer, sheet_name='商品信息', index=False)
        orders_df.to_excel(writer, sheet_name='订单表', index=False)
        order_items_df.to_excel(writer, sheet_name='订单明细', index=False)
    
    print(f"  [OK] 已保存: {sales_db_path}")
    
    # ========== 打印统计信息 ==========
    print("\n" + "=" * 60)
    print("数据生成完成！统计信息：")
    print("=" * 60)
    
    print("\n【数据库1: 客户管理数据库】")
    print(f"   - 客户信息: {len(customers_df)} 条记录")
    print(f"   - 收货地址: {len(addresses_df)} 条记录")
    print(f"   - 积分记录: {len(points_df)} 条记录")
    
    print("\n【数据库2: 销售订单数据库】")
    print(f"   - 商品信息: {len(products_df)} 条记录")
    print(f"   - 订单表: {len(orders_df)} 条记录")
    print(f"   - 订单明细: {len(order_items_df)} 条记录")
    
    print("\n【关联关系说明】")
    print("   两个数据库通过 '客户ID' 字段关联：")
    print("   - customer_management.xlsx 中的 '客户信息' 表")
    print("   - sales_orders.xlsx 中的 '订单表'")
    print("   可用于测试跨数据源的JOIN查询和统计分析")
    
    print("\n【测试查询示例】")
    print("   1. 查询某个客户的所有订单和订单明细")
    print("   2. 按客户会员等级统计销售额")
    print("   3. 按城市统计订单分布")
    print("   4. 分析商品销售排行")
    print("   5. 计算客户消费总额和积分情况")
    print("   6. 查询VIP客户的购买偏好")
    print("   7. 按时间段统计销售趋势")
    print("   8. 分析退款订单的原因分布")
    
    return customer_db_path, sales_db_path


if __name__ == '__main__':
    main()

