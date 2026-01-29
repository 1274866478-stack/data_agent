#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""初始化电商测试数据库"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/data_agent')

def get_connection(dbname='postgres'):
    """获取数据库连接"""
    url_parts = db_url.rsplit('/', 1)
    base_url = url_parts[0]
    conn = psycopg2.connect(f"{base_url}/{dbname}")
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

print("Step 1: 创建数据库...")
try:
    conn = get_connection('postgres')
    cursor = conn.cursor()
    cursor.execute('DROP DATABASE IF EXISTS ecommerce_test_db')
    print("  - Dropped existing database")
    cursor.execute('CREATE DATABASE ecommerce_test_db')
    print("  - Created ecommerce_test_db")
    conn.close()
except Exception as e:
    print(f"  Error: {e}")

print("\nStep 2: 读取SQL脚本...")
with open('scripts/init-ecommerce-test-db.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

print("\nStep 3: 执行SQL脚本...")
try:
    conn = get_connection('ecommerce_test_db')
    cursor = conn.cursor()

    # 按行分割，处理多行语句
    statements = []
    current_stmt = []
    in_function = False

    for line in sql_script.split('\n'):
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith('--'):
            continue

        current_stmt.append(line)

        # 检查语句结束
        if stripped.endswith(';'):
            stmt = '\n'.join(current_stmt)
            statements.append(stmt)
            current_stmt = []

    # 执行每个语句
    for i, stmt in enumerate(statements):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                cursor.execute(stmt)
            except Exception as e:
                # 忽略某些可预期的错误
                if 'already exists' not in str(e):
                    print(f"  Warning on statement {i+1}: {e}")

    print("  - SQL executed")

    print("\nStep 4: 验证数据...")
    tables = ['users', 'addresses', 'categories', 'products', 'orders', 'order_items', 'reviews']
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} rows")
        except Exception as e:
            print(f"  - {table}: Error - {e}")

    conn.close()
    print("\nDatabase initialization complete!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
