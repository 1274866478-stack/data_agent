# -*- coding: utf-8 -*-
"""
创建测试数据库 V2 - 10万条业务数据
==================================

简化版，使用更可靠的数据生成方式。

作者: BMad Master
版本: 2.0.0
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import random
import string

from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Date, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================================
# 配置
# ============================================================================
DATABASE_URL = "postgresql://postgres:password@localhost:5432/data_agent"

Base = declarative_base()


# ============================================================================
# 模型定义
# ============================================================================

class Region(Base):
    __tablename__ = 'regions'
    id = Column(Integer, primary_key=True)
    region_code = Column(String(10), unique=True, nullable=False)
    region_name = Column(String(100), nullable=False)
    country = Column(String(50), nullable=False)


class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    customer_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    region_id = Column(Integer, ForeignKey('regions.id'))
    register_date = Column(Date, nullable=False)
    status = Column(String(20), default='active')
    credit_level = Column(String(10))
    total_purchase = Column(Numeric(15, 2), default=0)


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    category_code = Column(String(20), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    unit_price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    status = Column(String(20), default='active')
    created_date = Column(Date, nullable=False)


class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    id = Column(Integer, primary_key=True)
    order_code = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    order_date = Column(DateTime, nullable=False)
    status = Column(String(20), default='pending')
    subtotal = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)


class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)


# ============================================================================
# 辅助函数
# ============================================================================

def generate_unique_code(prefix):
    """生成唯一编码"""
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"


def generate_name():
    """生成随机姓名"""
    surnames = "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗"
    names = "伟芳娜敏静秀英丽强磊军洋勇艳杰娟涛明超"
    return random.choice(surnames) + random.choice(names)


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 70)
    print("创建测试数据库 V2 - 10万条业务数据")
    print("=" * 70)

    # 创建引擎
    engine = create_engine(DATABASE_URL, echo=False)

    # 删除所有表
    print("\n[INFO] 删除现有表...")
    Base.metadata.drop_all(engine)

    # 创建所有表
    print("[INFO] 创建新表...")
    Base.metadata.create_all(engine)

    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        start_time = time.time()

        # 1. 创建地区
        print("\n[1/7] 创建地区数据...")
        regions_data = [
            Region(region_code=f"R{i:03d}", region_name=f"地区{i}", country="中国")
            for i in range(1, 51)
        ]
        session.add_all(regions_data)
        session.commit()
        print(f"[OK] 地区: {len(regions_data)} 条")

        # 2. 创建产品分类
        print("\n[2/7] 创建产品分类...")
        categories_data = [
            Category(category_code=f"CAT{i:03d}", category_name=f"分类{i}")
            for i in range(1, 51)
        ]
        session.add_all(categories_data)
        session.commit()
        print(f"[OK] 分类: {len(categories_data)} 条")

        # 3. 创建客户
        print("\n[3/7] 创建客户数据...")
        region_ids = [r.id for r in regions_data]
        base_date = datetime(2022, 1, 1)

        for i in range(10000):
            customer = Customer(
                customer_code=generate_unique_code("C"),
                name=generate_name(),
                email=f"customer{i}@example.com",
                phone=f"1{random.choice([3,5,7,8,9])}{random.randint(100000000, 999999999)}",
                region_id=random.choice(region_ids),
                register_date=(base_date + timedelta(days=random.randint(0, 730))).date(),
                status=random.choice(["active", "active", "active", "inactive"]),
                credit_level=random.choice(["A", "A", "B", "B", "C", "D"]),
                total_purchase=Decimal(str(round(random.uniform(0, 100000), 2)))
            )
            session.add(customer)

            if (i + 1) % 1000 == 0:
                session.commit()
                print(f"  进度: {i + 1}/10000")

        session.commit()
        print("[OK] 客户: 10000 条")

        # 4. 创建产品
        print("\n[4/7] 创建产品数据...")
        category_ids = [c.id for c in categories_data]

        for i in range(5000):
            product = Product(
                product_code=generate_unique_code("P"),
                name=f"产品{i+1}",
                category_id=random.choice(category_ids),
                unit_price=Decimal(str(round(random.uniform(10, 50000), 2))),
                stock_quantity=random.randint(0, 500),
                status=random.choice(["active", "active", "active", "discontinued"]),
                created_date=(base_date + timedelta(days=random.randint(0, 730))).date()
            )
            session.add(product)

            if (i + 1) % 500 == 0:
                session.commit()
                print(f"  进度: {i + 1}/5000")

        session.commit()
        print("[OK] 产品: 5000 条")

        # 5. 创建销售订单
        print("\n[5/7] 创建销售订单...")
        customer_ids = [c.id for c in session.query(Customer).all()]

        for i in range(50000):
            order = SalesOrder(
                order_code=generate_unique_code("O"),
                customer_id=random.choice(customer_ids),
                order_date=base_date + timedelta(
                    days=random.randint(0, 730),
                    hours=random.randint(8, 18)
                ),
                status=random.choice(["pending", "processing", "shipped", "delivered", "cancelled"]),
                subtotal=Decimal(str(round(random.uniform(100, 10000), 2))),
                total_amount=Decimal(str(round(random.uniform(100, 10000), 2)))
            )
            session.add(order)

            if (i + 1) % 5000 == 0:
                session.commit()
                print(f"  进度: {i + 1}/50000")

        session.commit()
        print("[OK] 订单: 50000 条")

        # 6. 创建订单明细
        print("\n[6/7] 创建订单明细...")
        order_ids = [o.id for o in session.query(SalesOrder).limit(50000).all()]
        product_ids = [p.id for p in session.query(Product).all()]

        for i in range(100000):
            quantity = random.randint(1, 10)
            unit_price = Decimal(str(round(random.uniform(10, 5000), 2)))

            item = OrderItem(
                order_id=random.choice(order_ids),
                product_id=random.choice(product_ids),
                quantity=quantity,
                unit_price=unit_price,
                subtotal=Decimal(str(float(unit_price) * quantity))
            )
            session.add(item)

            if (i + 1) % 10000 == 0:
                session.commit()
                print(f"  进度: {i + 1}/100000")

        session.commit()
        print("[OK] 订单明细: 100000 条")

        # 7. 更新订单金额
        print("\n[7/7] 更新订单金额...")
        session.execute(text("""
            UPDATE sales_orders so
            SET subtotal = (
                SELECT COALESCE(SUM(oi.subtotal), 0)
                FROM order_items oi
                WHERE oi.order_id = so.id
            ),
            total_amount = subtotal * 1.13
        """))
        session.commit()
        print("[OK] 订单金额更新完成")

        # 统计
        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("数据填充完成")
        print("=" * 70)
        print(f"  地区 (regions):          {session.query(Region).count():,} 条")
        print(f"  分类 (categories):       {session.query(Category).count():,} 条")
        print(f"  客户 (customers):        {session.query(Customer).count():,} 条")
        print(f"  产品 (products):         {session.query(Product).count():,} 条")
        print(f"  订单 (sales_orders):     {session.query(SalesOrder).count():,} 条")
        print(f"  明细 (order_items):      {session.query(OrderItem).count():,} 条")

        total = (
            session.query(Region).count() +
            session.query(Category).count() +
            session.query(Customer).count() +
            session.query(Product).count() +
            session.query(SalesOrder).count() +
            session.query(OrderItem).count()
        )

        print(f"\n[SUCCESS] 总计 {total:,} 条测试数据创建完成！")
        print(f"[INFO] 耗时: {elapsed:.1f} 秒")

        # 示例查询
        print("\n" + "=" * 70)
        print("示例复杂查询")
        print("=" * 70)
        print("""
-- 查询销售额 TOP 10 客户
SELECT c.name, COUNT(o.id) AS order_count,
       SUM(o.total_amount) AS total_spent
FROM customers c
JOIN sales_orders o ON c.id = o.customer_id
GROUP BY c.id, c.name
ORDER BY total_spent DESC
LIMIT 10;

-- 查询每个分类的产品数量
SELECT cat.category_name, COUNT(p.id) AS product_count
FROM categories cat
LEFT JOIN products p ON cat.id = p.category_id
GROUP BY cat.id, cat.category_name;

-- 查询月度销售趋势
SELECT DATE_TRUNC('month', order_date) AS month,
       COUNT(*) AS order_count,
       SUM(total_amount) AS total_sales
FROM sales_orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;
        """)

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] 数据填充失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    exit(main())
