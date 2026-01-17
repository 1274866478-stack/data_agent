"""
生成大型测试数据库并导入PostgreSQL

生成10万+条测试数据到ecommerce_large_db数据库

表结构：
1. users (用户表) - 100,000 条
2. products (产品表) - 10,000 条
3. orders (订单表) - 500,000 条
4. order_items (订单明细表) - 1,500,000 条
5. categories (分类表) - 100 条
6. reviews (评价表) - 300,000 条
"""

import os
import psycopg2
import random
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ecommerce_large_db',
    'user': 'postgres',
    'password': 'password'
}

# 设置随机种子
random.seed(42)
np.random.seed(42)

def get_db_connection(dbname='ecommerce_large_db'):
    """获取数据库连接"""
    config = DB_CONFIG.copy()
    config['database'] = dbname
    return psycopg2.connect(**config)

def init_database():
    """初始化数据库和表结构"""
    # 先连接到postgres数据库创建新数据库
    conn = get_db_connection('postgres')
    conn.autocommit = True
    cursor = conn.cursor()

    # 终止所有连接到目标数据库的会话
    cursor.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'ecommerce_large_db' AND pid <> pg_backend_pid();
    """)
    # 创建数据库
    cursor.execute("DROP DATABASE IF EXISTS ecommerce_large_db;")
    cursor.execute("CREATE DATABASE ecommerce_large_db;")
    cursor.close()
    conn.close()

    # 连接到新数据库
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()

    # 创建表
    print("创建数据库表...")

    # 1. 分类表
    cursor.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            parent_id INTEGER,
            description TEXT
        );
    """)

    # 2. 用户表
    cursor.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20),
            gender VARCHAR(10),
            birth_date DATE,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vip_level INTEGER DEFAULT 0,
            total_spent DECIMAL(12, 2) DEFAULT 0,
            is_active BOOLEAN DEFAULT true
        );
        CREATE INDEX idx_users_email ON users(email);
        CREATE INDEX idx_users_registration ON users(registration_date);
    """)

    # 3. 产品表
    cursor.execute("""
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            price DECIMAL(10, 2) NOT NULL,
            cost_price DECIMAL(10, 2),
            stock_quantity INTEGER DEFAULT 0,
            sales_count INTEGER DEFAULT 0,
            rating DECIMAL(3, 2) DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_products_category ON products(category_id);
        CREATE INDEX idx_products_price ON products(price);
    """)

    # 4. 订单表
    cursor.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(12, 2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            payment_method VARCHAR(20),
            shipping_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_orders_user ON orders(user_id);
        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_orders_status ON orders(status);
    """)

    # 5. 订单明细表
    cursor.execute("""
        CREATE TABLE order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id),
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(12, 2) NOT NULL
        );
        CREATE INDEX idx_order_items_order ON order_items(order_id);
        CREATE INDEX idx_order_items_product ON order_items(product_id);
    """)

    # 6. 评价表
    cursor.execute("""
        CREATE TABLE reviews (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            product_id INTEGER REFERENCES products(id),
            order_id INTEGER REFERENCES orders(id),
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_reviews_product ON reviews(product_id);
        CREATE INDEX idx_reviews_user ON reviews(user_id);
    """)

    cursor.close()
    conn.close()
    print("表创建完成！")

def generate_categories():
    """生成分类数据"""
    print("生成分类数据...")
    conn = get_db_connection()
    cursor = conn.cursor()

    categories = [
        ('电子产品', None, '手机、电脑、数码等'),
        ('服装鞋帽', None, '男装、女装、鞋类等'),
        ('家居用品', None, '家具、家纺、厨具等'),
        ('食品饮料', None, '零食、饮料、生鲜等'),
        ('图书文具', None, '图书、办公用品等'),
        ('运动户外', None, '运动器材、户外装备等'),
        ('美妆护肤', None, '护肤品、化妆品等'),
        ('母婴用品', None, '奶粉、尿裤、玩具等'),
    ]

    for cat in categories:
        cursor.execute("INSERT INTO categories (name, parent_id, description) VALUES (%s, %s, %s)", cat)

    # 添加子分类
    cursor.execute("SELECT id FROM categories WHERE parent_id IS NULL")
    parent_ids = [row[0] for row in cursor.fetchall()]

    subcategories = []
    for parent_id in parent_ids:
        for i in range(10):
            subcategories.append((f'子分类-{parent_id}-{i}', parent_id, f'这是子分类{i}的描述'))

    cursor.executemany("INSERT INTO categories (name, parent_id, description) VALUES (%s, %s, %s)", subcategories)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"分类数据生成完成！共 {8 + len(parent_ids) * 10} 条")

def generate_users(count=100000):
    """生成用户数据"""
    print(f"生成 {count} 个用户...")
    conn = get_db_connection()
    cursor = conn.cursor()

    first_names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '洋', '勇', '军', '杰', '娟', '涛', '明']
    last_names = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '胡', '郭']

    # 批量插入
    batch_size = 10000
    for i in tqdm(range(0, count, batch_size), desc="插入用户"):
        batch_users = []
        for j in range(batch_size):
            if i + j >= count:
                break

            reg_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))
            birth_date = datetime(1970, 1, 1) + timedelta(days=random.randint(0, 15000))

            user = (
                f"user_{i+j}_{random.randint(1000, 9999)}",
                f"user{i+j}@example.com",
                f"1{random.randint(3, 9)}{random.randint(100000000, 999999999)}",
                random.choice(['男', '女']),
                birth_date,
                reg_date,
                random.randint(0, 5),
                round(random.uniform(0, 100000), 2)
            )
            batch_users.append(user)

        cursor.executemany("""
            INSERT INTO users (username, email, phone, gender, birth_date, registration_date, vip_level, total_spent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, batch_users)
        conn.commit()

    cursor.close()
    conn.close()
    print(f"用户数据生成完成！共 {count} 条")

def generate_products(count=10000):
    """生成产品数据"""
    print(f"生成 {count} 个产品...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取分类ID
    cursor.execute("SELECT id FROM categories WHERE parent_id IS NOT NULL")
    category_ids = [row[0] for row in cursor.fetchall()]

    product_names = [
        'iPhone', '华为', '小米', 'OPPO', 'vivo', '三星', 'MacBook', 'ThinkPad', '戴尔', '华硕',
        '耐克', '阿迪达斯', '李宁', '安踏', '优衣库', 'ZARA', 'H&M', 'GXG', '太平鸟', '森马',
        '海尔', '美的', '格力', '小米', '飞利浦', '松下', '索尼', 'JBL', '博朗', '飞科',
        '乐事', '可口可乐', '百事可乐', '康师傅', '统一', '旺旺', '奥利奥', '德芙', '费列罗', '好时',
        '三体', '哈利波特', '新华字典', '五年高考', '编程思想', '算法导论', '深度学习', '经济学原理'
    ]

    batch_size = 5000
    for i in tqdm(range(0, count, batch_size), desc="插入产品"):
        batch_products = []
        for j in range(batch_size):
            if i + j >= count:
                break

            price = round(random.uniform(10, 20000), 2)
            cost_price = round(price * random.uniform(0.5, 0.8), 2)

            product = (
                f"{random.choice(product_names)}-{random.randint(1, 1000)}",
                random.choice(category_ids),
                price,
                cost_price,
                random.randint(0, 5000),
                random.randint(0, 10000),
                round(random.uniform(3, 5), 1),
                random.randint(0, 5000)
            )
            batch_products.append(product)

        cursor.executemany("""
            INSERT INTO products (name, category_id, price, cost_price, stock_quantity, sales_count, rating, review_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, batch_products)
        conn.commit()

    cursor.close()
    conn.close()
    print(f"产品数据生成完成！共 {count} 条")

def generate_orders(count=500000):
    """生成订单数据"""
    print(f"生成 {count} 个订单...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取用户ID范围
    cursor.execute("SELECT MIN(id), MAX(id) FROM users")
    user_min, user_max = cursor.fetchone()

    order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    payment_methods = ['wechat', 'alipay', 'card', 'bank_transfer']

    batch_size = 10000
    for i in tqdm(range(0, count, batch_size), desc="插入订单"):
        batch_orders = []
        for j in range(batch_size):
            if i + j >= count:
                break

            order_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))
            total_amount = round(random.uniform(50, 50000), 2)

            order = (
                random.randint(user_min, user_max),
                order_date,
                total_amount,
                random.choice(order_statuses),
                random.choice(payment_methods),
                f"上海市浦东新区{random.randint(1, 999)}号"
            )
            batch_orders.append(order)

        cursor.executemany("""
            INSERT INTO orders (user_id, order_date, total_amount, status, payment_method, shipping_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, batch_orders)
        conn.commit()

    cursor.close()
    conn.close()
    print(f"订单数据生成完成！共 {count} 条")

def generate_order_items():
    """生成订单明细数据"""
    print("生成订单明细数据...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取订单和产品ID范围
    cursor.execute("SELECT MIN(id), MAX(id) FROM orders")
    order_min, order_max = cursor.fetchone()

    cursor.execute("SELECT MIN(id), MAX(id) FROM products")
    product_min, product_max = cursor.fetchone()

    # 为每个订单生成1-10个明细项
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]

    batch_size = 50000
    total_items = 0

    for order_id in tqdm(range(1, order_count + 1), desc="插入订单明细"):
        num_items = random.randint(1, 10)
        batch_items = []

        for _ in range(num_items):
            quantity = random.randint(1, 5)
            unit_price = round(random.uniform(20, 5000), 2)

            item = (
                order_id,
                random.randint(product_min, product_max),
                quantity,
                unit_price,
                round(quantity * unit_price, 2)
            )
            batch_items.append(item)

            if len(batch_items) >= batch_size:
                cursor.executemany("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, batch_items)
                conn.commit()
                total_items += len(batch_items)
                batch_items = []

        if batch_items:
            cursor.executemany("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, batch_items)
            conn.commit()
            total_items += len(batch_items)

    cursor.close()
    conn.close()
    print(f"订单明细数据生成完成！共 {total_items} 条")

def generate_reviews(count=300000):
    """生成评价数据"""
    print(f"生成 {count} 条评价...")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MIN(id), MAX(id) FROM users")
    user_min, user_max = cursor.fetchone()

    cursor.execute("SELECT MIN(id), MAX(id) FROM products")
    product_min, product_max = cursor.fetchone()

    cursor.execute("SELECT MIN(id), MAX(id) FROM orders")
    order_min, order_max = cursor.fetchone()

    review_comments = [
        '非常好，很满意！', '质量不错，值得购买', '物流很快，包装完好',
        '性价比高，推荐购买', '一般般吧', '质量不太好，有点失望',
        '非常棒，会回购', '服务态度好，产品质量好', '价格实惠，质量不错',
        '用了一段时间，感觉还可以', '超出预期，非常惊喜', '不太推荐',
    ]

    batch_size = 10000
    for i in tqdm(range(0, count, batch_size), desc="插入评价"):
        batch_reviews = []
        for j in range(batch_size):
            if i + j >= count:
                break

            review = (
                random.randint(user_min, user_max),
                random.randint(product_min, product_max),
                random.randint(order_min, order_max),
                random.randint(1, 5),
                random.choice(review_comments)
            )
            batch_reviews.append(review)

        cursor.executemany("""
            INSERT INTO reviews (user_id, product_id, order_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, batch_reviews)
        conn.commit()

    cursor.close()
    conn.close()
    print(f"评价数据生成完成！共 {count} 条")

def print_statistics():
    """打印数据统计"""
    conn = get_db_connection()
    cursor = conn.cursor()

    tables = ['users', 'products', 'orders', 'order_items', 'categories', 'reviews']

    print("\n" + "=" * 60)
    print("数据统计信息")
    print("=" * 60)

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:15s}: {count:>12,} 条")

    cursor.close()
    conn.close()

    print("=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("大型测试数据库生成工具")
    print("=" * 60)
    print("\n目标数据库: ecommerce_large_db")
    print("数据规模:")
    print("  - users:       100,000 条")
    print("  - products:     10,000 条")
    print("  - orders:      500,000 条")
    print("  - order_items: ~1,500,000 条")
    print("  - categories:       100 条")
    print("  - reviews:     300,000 条")
    print("\n总计约 2,400,000+ 条数据")
    print("=" * 60)
    print()

    try:
        init_database()
        generate_categories()
        generate_users(100000)
        generate_products(10000)
        generate_orders(500000)
        generate_order_items()
        generate_reviews(300000)
        print_statistics()

        print("\n[OK] 测试数据库生成完成！")
        print(f"\n连接字符串: postgresql://postgres:password@localhost:5432/ecommerce_large_db")

    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
