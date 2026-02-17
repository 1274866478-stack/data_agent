#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在Neon数据库上初始化电商测试数据库"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

db_url = os.getenv('DATABASE_URL', '')

# 切换到测试数据库
test_db_url = db_url.rsplit('/', 1)[0] + '/ecommerce_test_db'

print("Step 1: 读取SQL脚本...")
with open('scripts/init-ecommerce-test-db.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

print("\nStep 2: 连接到Neon数据库...")
try:
    # 先连接到默认数据库（neondb）
    conn = psycopg2.connect(db_url)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # 检查是否需要创建数据库（Neon可能不支持CREATE DATABASE）
    print("  Checking ecommerce_test_db existence...")
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='ecommerce_test_db'")
    if not cursor.fetchone():
        print("  Database does not exist, attempting to create...")
        try:
            cursor.execute('CREATE DATABASE ecommerce_test_db')
            print("  Database created successfully")
        except Exception as e:
            # Neon可能不支持CREATE DATABASE，直接使用schema
            print(f"  Cannot create database (Neon limitation): {e}")
            print("  Will create tables in the default database schema instead")
            test_db_url = db_url  # 使用原数据库URL

    conn.close()

except Exception as e:
    print(f"Warning: {e}")
    print("Proceeding with table creation...")

print("\nStep 3: 执行SQL脚本...")
try:
    # 连接到目标数据库
    conn = psycopg2.connect(test_db_url)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # 删除已存在的表（按依赖顺序）
    tables_to_drop = ['reviews', 'order_items', 'orders', 'products', 'categories', 'users', 'addresses']
    for table in tables_to_drop:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
            print(f"  Dropped table: {table}")
        except Exception as e:
            print(f"  Warning dropping {table}: {e}")

    # 按行分割，处理多行语句
    statements = []
    current_stmt = []

    for line in sql_script.split('\n'):
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith('--'):
            continue

        # 跳过CREATE DATABASE和EXTENSION语句
        if any(keyword in stripped.upper() for keyword in ['CREATE DATABASE', 'CREATE EXTENSION', 'DROP DATABASE']):
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
                # 某些语句可能失败，继续执行
                if 'already exists' not in str(e) and 'does not exist' not in str(e):
                    print(f"  Warning on statement {i+1}: {e}")

    print("  SQL executed")

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
    print(f"Test database URL: {test_db_url[:60]}...")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
