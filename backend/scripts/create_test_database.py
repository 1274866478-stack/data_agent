# -*- coding: utf-8 -*-
"""
创建测试数据库 - 10万条业务数据
==================================

创建一个完整的电商业务数据库，包含：
- 10个核心表
- 外键关系
- 约10万条测试数据
- 支持复杂查询测试

作者: BMad Master
版本: 1.0.0
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
import string

from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric, DateTime,
    ForeignKey, Text, Boolean, Date, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

# ============================================================================
# 配置
# ============================================================================
DATABASE_URL = "postgresql://postgres:password@localhost:5432/data_agent"

# 数据量配置
NUM_CUSTOMERS = 10000
NUM_PRODUCTS = 5000
NUM_CATEGORIES = 50
NUM_SUPPLIERS = 200
NUM_REGIONS = 50
NUM_ORDERS = 50000
NUM_ORDER_ITEMS = 100000

Base = declarative_base()


# ============================================================================
# 模型定义
# ============================================================================

class Region(Base):
    """地区表"""
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True)
    region_code = Column(String(10), unique=True, nullable=False)
    region_name = Column(String(100), nullable=False)
    country = Column(String(50), nullable=False)
    level = Column(String(20))  # 'country', 'province', 'city'


class Customer(Base):
    """客户表"""
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    customer_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    phone = Column(String(20))
    region_id = Column(Integer, ForeignKey('regions.id'))
    address = Column(Text)
    register_date = Column(Date, nullable=False)
    status = Column(String(20), default='active')  # active, inactive
    credit_level = Column(String(10))  # A, B, C, D
    total_purchase = Column(Numeric(15, 2), default=0)


class Category(Base):
    """产品分类表"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    category_code = Column(String(20), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    description = Column(Text)
    level = Column(Integer, default=1)


class Supplier(Base):
    """供应商表"""
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    supplier_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    contact_person = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    region_id = Column(Integer, ForeignKey('regions.id'))
    address = Column(Text)
    rating = Column(Numeric(3, 2))  # 0.00-5.00
    status = Column(String(20), default='active')


class Product(Base):
    """产品表"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    product_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    unit_price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2))
    description = Column(Text)
    unit = Column(String(20))  # 个, 台, 套, etc
    stock_quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=10)
    max_stock = Column(Integer, default=1000)
    reorder_level = Column(Integer, default=20)
    status = Column(String(20), default='active')  # active, discontinued
    created_date = Column(Date, nullable=False)
    updated_date = Column(Date)
    weight = Column(Numeric(8, 2))
    warranty_months = Column(Integer)


class Inventory(Base):
    """库存表"""
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'))
    quantity = Column(Integer, default=0)
    warehouse_location = Column(String(50))
    last_restock_date = Column(Date)


class SalesOrder(Base):
    """销售订单表"""
    __tablename__ = 'sales_orders'

    id = Column(Integer, primary_key=True)
    order_code = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    order_date = Column(DateTime, nullable=False)
    required_date = Column(Date)
    shipped_date = Column(Date)
    delivery_region_id = Column(Integer, ForeignKey('regions.id'))
    status = Column(String(20), default='pending')  # pending, processing, shipped, delivered, cancelled
    payment_method = Column(String(30))  # cash, credit_card, wire_transfer, alipay, wechat
    payment_status = Column(String(20), default='unpaid')  # unpaid, partial, paid
    subtotal = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    shipping_fee = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OrderItem(Base):
    """订单明细表"""
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0)
    subtotal = Column(Numeric(15, 2), nullable=False)
    notes = Column(Text)


class SalesReturn(Base):
    """销售退货表"""
    __tablename__ = 'sales_returns'

    id = Column(Integer, primary_key=True)
    return_code = Column(String(30), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey('sales_orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    return_date = Column(Date, nullable=False)
    reason = Column(String(200))
    refund_amount = Column(Numeric(10, 2))
    status = Column(String(20), default='pending')  # pending, approved, rejected, completed


# ============================================================================
# 数据生成器
# ============================================================================

class DataGenerator:
    """测试数据生成器"""

    # 姓氏和名字库
    SURNAMES = [
        "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "吴", "周",
        "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗"
    ]

    NAMES = [
        "伟", "芳", "娜", "敏", "静", "秀英", "丽", "强", "磊", "军",
        "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀兰", "霞"
    ]

    # 产品分类
    CATEGORY_NAMES = [
        "电子产品", "家用电器", "服装鞋帽", "食品饮料", "日用百货",
        "图书文具", "运动户外", "美妆护肤", "母婴用品", "家居建材"
    ]

    # 产品名称模板
    PRODUCT_TEMPLATES = [
        "{brand}{type}{spec}",
        "{category}{feature}版",
        "{brand}{series}{size}寸",
        "{category}{style}款{color}",
        "{brand}新款{category}"
    ]

    BRANDS = ["小米", "华为", "苹果", "联想", "戴尔", "三星", "索尼", "海尔", "格力", "美的"]
    TYPES = ["手机", "电脑", "平板", "耳机", "音箱", "键盘", "鼠标", "显示器", "路由器", "摄像头"]
    SPECS = ["Pro", "Max", "Plus", "Ultra", "Lite", "Standard", "Premium", "Elite"]
    FEATURES = ["智能", "无线", "便携", "高清", "防水", "静音", "节能", "环保"]
    SERIES = ["X系列", "P系列", "Mate系列", "Air系列", "Pro系列", "ThinkPad", "IdeaPad"]
    SIZES = ["13", "14", "15", "17", "21", "24", "27", "32"]
    STYLES = ["时尚", "商务", "运动", "休闲", "简约", "复古", "豪华"]
    COLORS = ["黑色", "白色", "银色", "金色", "蓝色", "红色"]

    # 地区数据
    PROVINCES = [
        "北京市", "上海市", "天津市", "重庆市", "广东省", "江苏省", "浙江省", "四川省",
        "湖北省", "湖南省", "河南省", "河北省", "山东省", "山西省", "陕西省", "辽宁省",
        "吉林省", "黑龙江省", "安徽省", "福建省", "江西省", "云南省", "贵州省", "甘肃省"
    ]

    CITIES = {
        "北京市": ["东城区", "西城区", "朝阳区", "海淀区", "丰台区"],
        "上海市": ["黄浦区", "徐汇区", "静安区", "普陀区", "浦东新区"],
        "广东省": ["广州市", "深圳市", "珠海市", "佛山市", "东莞市"],
        "江苏省": ["南京市", "苏州市", "无锡市", "常州市", "徐州市"],
        "浙江省": ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市"],
        "四川省": ["成都市", "绵阳市", "德阳市", "宜宾市", "南充市"],
    }

    @staticmethod
    def generate_name():
        """生成随机姓名"""
        surname = random.choice(DataGenerator.SURNAMES)
        name = random.choice(DataGenerator.NAMES)
        return f"{surname}{name}"

    @staticmethod
    def generate_email(name):
        """生成邮箱"""
        domains = ["qq.com", "163.com", "gmail.com", "outlook.com", "sina.com"]
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{username}@{random.choice(domains)}"

    @staticmethod
    def generate_phone():
        """生成手机号"""
        return f"1{random.choice([3, 5, 7, 8, 9])}{random.randint(100000000, 999999999)}"

    @staticmethod
    def generate_address(region_name):
        """生成地址"""
        street = random.choice(["建设路", "人民路", "解放路", "中山路", "和平路", "文化路", "科技路"])
        building = random.choice(["大厦", "广场", "中心", "花园", "小区", "公寓"])
        number = random.randint(1, 999)
        return f"{region_name}{street}{number}号{building}"

    @staticmethod
    def generate_product_name():
        """生成产品名称"""
        template = random.choice(DataGenerator.PRODUCT_TEMPLATES)
        return template.format(
            brand=random.choice(DataGenerator.BRANDS),
            category=random.choice(DataGenerator.CATEGORY_NAMES[:5]),
            type=random.choice(DataGenerator.TYPES),
            spec=random.choice(DataGenerator.SPECS),
            feature=random.choice(DataGenerator.FEATURES),
            series=random.choice(DataGenerator.SERIES),
            size=random.choice(DataGenerator.SIZES),
            style=random.choice(DataGenerator.STYLES),
            color=random.choice(DataGenerator.COLORS)
        )

    @staticmethod
    def generate_code(prefix, length=8):
        """生成编码（使用UUID确保唯一性）"""
        unique_id = str(uuid.uuid4()).replace('-', '')[:length]
        return f"{prefix}{unique_id}"


# ============================================================================
# 数据库创建和填充
# ============================================================================

async def create_database():
    """创建数据库和表"""
    print("=" * 70)
    print("开始创建测试数据库")
    print("=" * 70)

    # 创建引擎
    engine = create_engine(DATABASE_URL, echo=False)

    # 删除所有表（如果存在）
    print("\n[INFO] 删除现有表...")
    Base.metadata.drop_all(engine)

    # 创建所有表
    print("[INFO] 创建新表...")
    Base.metadata.create_all(engine)

    print("[SUCCESS] 数据库表创建完成")
    return engine


def populate_database(engine):
    """填充测试数据"""
    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n" + "=" * 70)
    print("开始填充测试数据")
    print("=" * 70)

    try:
        # 1. 创建地区数据
        print("\n[1/8] 创建地区数据...")
        regions = []
        region_id_map = {}

        # 国家级
        china = Region(
            region_code="CN",
            region_name="中国",
            country="中国",
            level="country"
        )
        regions.append(china)
        session.add(china)
        session.flush()
        region_id_map["中国"] = china.id

        # 省级
        for province in DataGenerator.PROVINCES[:NUM_REGIONS // 2]:
            region = Region(
                region_code=DataGenerator.generate_code("P", 4),
                region_name=province,
                country="中国",
                level="province"
            )
            regions.append(region)
            session.add(region)
            session.flush()
            region_id_map[province] = region.id

            # 市级
            if province in DataGenerator.CITIES:
                for city in DataGenerator.CITIES[province][:3]:
                    city_region = Region(
                        region_code=DataGenerator.generate_code("C", 4),
                        region_name=city,
                        country="中国",
                        level="city"
                    )
                    regions.append(city_region)
                    session.add(city_region)
                    session.flush()
                    region_id_map[city] = city_region.id

        session.commit()
        print(f"[OK] 地区数据创建完成: {len(regions)} 条")

        # 2. 创建产品分类
        print("\n[2/8] 创建产品分类...")
        categories = []
        category_id_map = {}

        # 一级分类
        for idx, cat_name in enumerate(DataGenerator.CATEGORY_NAMES[:NUM_CATEGORIES // 5]):
            code = DataGenerator.generate_code("CAT", 4)
            category = Category(
                category_code=code,
                category_name=cat_name,
                description=f"{cat_name}分类",
                level=1
            )
            categories.append(category)
            session.add(category)
            session.flush()
            category_id_map[cat_name] = category.id

            # 二级分类
            for j in range(5):
                sub_name = f"{cat_name}-子类{j+1}"
                sub_category = Category(
                    category_code=DataGenerator.generate_code("SCAT", 4),
                    category_name=sub_name,
                    parent_id=category.id,
                    description=f"{sub_name}详情",
                    level=2
                )
                categories.append(sub_category)
                session.add(sub_category)

        session.commit()
        print(f"[OK] 产品分类创建完成: {len(categories)} 条")

        # 3. 创建供应商
        print("\n[3/8] 创建供应商...")
        suppliers = []

        for i in range(NUM_SUPPLIERS):
            region_id = random.choice(list(region_id_map.values()))
            supplier = Supplier(
                supplier_code=DataGenerator.generate_code("SUP", 6),
                name=f"{DataGenerator.generate_name()}供应商",
                contact_person=DataGenerator.generate_name(),
                phone=DataGenerator.generate_phone(),
                email=DataGenerator.generate_email("supplier"),
                region_id=region_id if random.random() > 0.3 else None,
                address=DataGenerator.generate_address("某地区"),
                rating=Decimal(str(round(random.uniform(3.0, 5.0), 2))),
                status=random.choice(["active", "active", "active", "inactive"])
            )
            suppliers.append(supplier)

        session.bulk_save_objects(suppliers)
        session.commit()
        print(f"[OK] 供应商创建完成: {len(suppliers)} 条")

        # 4. 创建产品
        print("\n[4/8] 创建产品...")
        category_ids = [c.id for c in categories if c.level == 1]
        supplier_ids = [s.id for s in suppliers]

        base_date = datetime(2023, 1, 1)

        for i in range(NUM_PRODUCTS):
            category_id = random.choice(category_ids)
            supplier_id = random.choice(supplier_ids) if random.random() > 0.1 else None
            unit_price = Decimal(str(round(random.uniform(10, 50000), 2)))
            cost_price = unit_price * Decimal(str(round(random.uniform(0.5, 0.8), 2)))

            created_date = base_date + timedelta(days=random.randint(0, 730))

            product = Product(
                product_code=DataGenerator.generate_code("PROD", 12),
                name=DataGenerator.generate_product_name(),
                category_id=category_id,
                supplier_id=supplier_id,
                unit_price=unit_price,
                cost_price=cost_price,
                description=f"优质{DataGenerator.generate_product_name()}，性价比高",
                unit=random.choice(["个", "台", "套", "件", "箱", "包"]),
                stock_quantity=random.randint(0, 500),
                min_stock=random.randint(5, 20),
                max_stock=random.randint(500, 2000),
                reorder_level=random.randint(10, 50),
                status=random.choice(["active", "active", "active", "discontinued"]),
                created_date=created_date.date(),
                updated_date=created_date.date() + timedelta(days=random.randint(0, 30)),
                weight=Decimal(str(round(random.uniform(0.1, 50), 2))) if random.random() > 0.5 else None,
                warranty_months=random.choice([6, 12, 18, 24, 36]) if random.random() > 0.3 else None
            )
            session.add(product)

            # 每500条提交一次
            if (i + 1) % 500 == 0:
                session.commit()
                print(f"  进度: {i + 1}/{NUM_PRODUCTS}")

        session.commit()
        print(f"[OK] 产品创建完成: {NUM_PRODUCTS} 条")

        # 5. 创建客户
        print("\n[5/8] 创建客户...")
        customers = []
        base_date = datetime(2022, 1, 1)

        for i in range(NUM_CUSTOMERS):
            region_id = random.choice(list(region_id_map.values()))
            register_date = base_date + timedelta(days=random.randint(0, 730))

            customer = Customer(
                customer_code=DataGenerator.generate_code("CUST", 8),
                name=DataGenerator.generate_name(),
                email=DataGenerator.generate_email("customer"),
                phone=DataGenerator.generate_phone(),
                region_id=region_id if random.random() > 0.2 else None,
                address=DataGenerator.generate_address("某地区"),
                register_date=register_date.date(),
                status=random.choice(["active", "active", "active", "inactive"]),
                credit_level=random.choice(["A", "A", "B", "B", "C", "D"]),
                total_purchase=Decimal(str(round(random.uniform(0, 100000), 2)))
            )
            customers.append(customer)

            # 每1000条提交一次
            if len(customers) % 1000 == 0:
                session.bulk_save_objects(customers)
                session.commit()
                print(f"  进度: {len(customers)}/{NUM_CUSTOMERS}")

        if customers:
            session.bulk_save_objects(customers)
            session.commit()

        print(f"[OK] 客户创建完成: {len(customers)} 条")

        # 6. 创建库存
        print("\n[6/8] 创建库存...")
        inventories = []
        product_ids = [p.id for p in products[:500]]  # 只给部分产品创建库存
        region_ids = list(region_id_map.values())

        for product_id in product_ids:
            # 每个产品在1-3个地区有库存
            num_regions = random.randint(1, 3)
            for region_id in random.sample(region_ids, num_regions):
                inventory = Inventory(
                    product_id=product_id,
                    region_id=region_id,
                    quantity=random.randint(0, 500),
                    warehouse_location=f"仓库{random.randint(1, 10)}-{random.randint(1, 100)}号位",
                    last_restock_date=datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
                )
                inventories.append(inventory)

        session.bulk_save_objects(inventories)
        session.commit()
        print(f"[OK] 库存创建完成: {len(inventories)} 条")

        # 7. 创建销售订单
        print("\n[7/8] 创建销售订单...")
        orders = []
        customer_ids = [c.id for c in customers]
        base_date = datetime(2023, 1, 1)

        for i in range(NUM_ORDERS):
            customer_id = random.choice(customer_ids)
            order_date = base_date + timedelta(
                days=random.randint(0, 730),
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59)
            )

            required_date = order_date + timedelta(days=random.randint(1, 30))

            shipped_date = None
            status = random.choice([
                "pending", "processing", "shipped", "delivered", "delivered", "cancelled"
            ])

            if status in ["shipped", "delivered"]:
                shipped_date = order_date + timedelta(days=random.randint(1, 10))

            delivery_region_id = random.choice(list(region_id_map.values()))

            payment_method = random.choice(["cash", "credit_card", "alipay", "wechat", "wire_transfer"])
            payment_status = random.choice(["paid", "paid", "paid", "unpaid", "partial"])

            order = SalesOrder(
                order_code=DataGenerator.generate_code("ORD", 10),
                customer_id=customer_id,
                order_date=order_date,
                required_date=required_date.date() if required_date else None,
                shipped_date=shipped_date,
                delivery_region_id=delivery_region_id,
                status=status,
                payment_method=payment_method,
                payment_status=payment_status,
                notes="备注信息" if random.random() > 0.7 else None
            )
            orders.append(order)

            # 每1000条提交一次
            if len(orders) % 1000 == 0:
                session.bulk_save_objects(orders)
                session.commit()
                print(f"  进度: {len(orders)}/{NUM_ORDERS}")

        if orders:
            session.bulk_save_objects(orders)
            session.commit()

        print(f"[OK] 销售订单创建完成: {len(orders)} 条")

        # 8. 创建订单明细
        print("\n[8/8] 创建订单明细...")
        order_items = []
        order_ids = [o.id for o in orders]
        product_ids = [p.id for p in products]

        for i in range(NUM_ORDER_ITEMS):
            order_id = random.choice(order_ids)
            product_id = random.choice(product_ids)

            quantity = random.randint(1, 10)
            unit_price = Decimal(str(round(random.uniform(10, 5000), 2)))
            discount = Decimal(str(round(random.uniform(0, 0.3), 2)))
            subtotal = unit_price * quantity * (Decimal('1') - discount)

            order_item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                subtotal=subtotal,
                notes=None
            )
            order_items.append(order_item)

            # 每5000条提交一次
            if len(order_items) % 5000 == 0:
                session.bulk_save_objects(order_items)
                session.commit()
                print(f"  进度: {len(order_items)}/{NUM_ORDER_ITEMS}")

        if order_items:
            session.bulk_save_objects(order_items)
            session.commit()

        print(f"[OK] 订单明细创建完成: {len(order_items)} 条")

        # 9. 更新订单金额
        print("\n[9/9] 更新订单金额...")
        session.execute("""
            UPDATE sales_orders
            SET subtotal = (
                SELECT COALESCE(SUM(subtotal), 0)
                FROM order_items
                WHERE order_items.order_id = sales_orders.id
            ),
            tax_amount = subtotal * 0.13,
            shipping_fee = CASE WHEN subtotal >= 500 THEN 0 ELSE 20 END,
            discount_amount = CASE WHEN subtotal >= 1000 THEN subtotal * 0.05 ELSE 0 END,
            total_amount = (
                (SELECT COALESCE(SUM(subtotal), 0)
                 FROM order_items
                 WHERE order_items.order_id = sales_orders.id)
                * 1.13
                + CASE WHEN (SELECT COALESCE(SUM(subtotal), 0) FROM order_items WHERE order_items.order_id = sales_orders.id) >= 500 THEN 0 ELSE 20 END
                - CASE WHEN (SELECT COALESCE(SUM(subtotal), 0) FROM order_items WHERE order_items.order_id = sales_orders.id) >= 1000
                       THEN (SELECT COALESCE(SUM(subtotal), 0) FROM order_items WHERE order_items.order_id = sales_orders.id) * 0.05 ELSE 0 END
            )
        """)

        session.commit()
        print("[OK] 订单金额更新完成")

        # 10. 创建一些退货记录
        print("\n[10/10] 创建退货记录...")
        returns = []
        num_returns = NUM_ORDERS // 50  # 约1000条退货

        for i in range(num_returns):
            order_id = random.choice(order_ids)
            product_id = random.choice(product_ids)

            return_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 730))

            sales_return = SalesReturn(
                return_code=DataGenerator.generate_code("RTN", 10),
                order_id=order_id,
                product_id=product_id,
                quantity=random.randint(1, 5),
                return_date=return_date.date(),
                reason=random.choice([
                    "质量问题", "不符合预期", "尺寸不合适", "损坏", "发错货", "其他原因"
                ]),
                refund_amount=Decimal(str(round(random.uniform(50, 5000), 2))),
                status=random.choice(["pending", "approved", "rejected", "completed"])
            )
            returns.append(sales_return)

        session.bulk_save_objects(returns)
        session.commit()
        print(f"[OK] 退货记录创建完成: {len(returns)} 条")

        # 统计信息
        print("\n" + "=" * 70)
        print("数据填充完成统计")
        print("=" * 70)
        print(f"  地区 (regions):          {session.query(Region).count():,} 条")
        print(f"  产品分类 (categories):    {session.query(Category).count():,} 条")
        print(f"  供应商 (suppliers):      {session.query(Supplier).count():,} 条")
        print(f"  产品 (products):         {session.query(Product).count():,} 条")
        print(f"  库存 (inventory):        {session.query(Inventory).count():,} 条")
        print(f"  客户 (customers):        {session.query(Customer).count():,} 条")
        print(f"  销售订单 (sales_orders): {session.query(SalesOrder).count():,} 条")
        print(f"  订单明细 (order_items):  {session.query(OrderItem).count():,} 条")
        print(f"  退货记录 (sales_returns): {session.query(SalesReturn).count():,} 条")
        print("=" * 70)

        total = (
            session.query(Region).count() +
            session.query(Category).count() +
            session.query(Supplier).count() +
            session.query(Product).count() +
            session.query(Inventory).count() +
            session.query(Customer).count() +
            session.query(SalesOrder).count() +
            session.query(OrderItem).count() +
            session.query(SalesReturn).count()
        )
        print(f"\n[SUCCESS] 总计 {total:,} 条测试数据创建完成！")
        print("\n数据库已准备就绪，可以开始测试复杂查询！")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] 数据填充失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主函数"""
    import asyncio

    print("\n" + "=" * 70)
    print("测试数据库生成器")
    print("Data Agent V4 - 测试数据库创建工具")
    print("=" * 70)

    print(f"\n[CONFIG] 数据库URL: {DATABASE_URL}")
    print(f"[CONFIG] 预计数据量: 约 {NUM_CUSTOMERS + NUM_PRODUCTS + NUM_ORDERS + NUM_ORDER_ITEMS:,} 条")

    try:
        # 创建数据库和表
        engine = asyncio.run(create_database())

        # 填充数据
        populate_database(engine)

        print("\n[SUCCESS] 测试数据库创建完成！")

        # 显示示例查询
        print("\n" + "=" * 70)
        print("示例复杂查询")
        print("=" * 70)

        print("""
1. 查询每个地区月度销售额TOP 10:
   SELECT r.region_name, DATE_TRUNC('month', so.order_date) AS month,
          SUM(so.total_amount) AS total_sales
   FROM sales_orders so
   JOIN customers c ON so.customer_id = c.id
   JOIN regions r ON c.region_id = r.id
   GROUP BY r.region_name, DATE_TRUNC('month', so.order_date)
   ORDER BY total_sales DESC
   LIMIT 10;

2. 查询销售额最高的产品类别:
   SELECT cat.category_name, SUM(oi.subtotal) AS category_sales
   FROM order_items oi
   JOIN products p ON oi.product_id = p.id
   JOIN categories cat ON p.category_id = cat.id
   GROUP BY cat.category_name
   ORDER BY category_sales DESC;

3. 查询客户购买行为分析:
   SELECT c.name, COUNT(so.id) AS order_count,
          SUM(so.total_amount) AS total_spent,
          AVG(so.total_amount) AS avg_order_value
   FROM customers c
   LEFT JOIN sales_orders so ON c.id = so.customer_id
   GROUP BY c.id, c.name
   ORDER BY total_spent DESC
   LIMIT 20;
        """)

    except Exception as e:
        print(f"\n[ERROR] 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
