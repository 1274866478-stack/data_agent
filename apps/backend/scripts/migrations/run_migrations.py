"""
数据库迁移执行器

执行所有迁移脚本
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from psycopg2 import sql


def run_migration(conn, sql_file: str):
    """执行单个迁移文件"""
    print(f"执行迁移: {sql_file}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    cursor = conn.cursor()

    # 分割 SQL 语句 - 改进版本，支持多行字符串
    statements = []
    current_statement = []
    in_single_quote = False
    in_double_quote = False

    for line in sql_content.split('\n'):
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith('--'):
            continue

        # 追踪引号状态
        for char in line:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote

        current_statement.append(line)

        # 如果不在字符串内且以分号结尾，则语句结束
        if not in_single_quote and not in_double_quote and stripped.endswith(';'):
            statements.append('\n'.join(current_statement))
            current_statement = []
            in_single_quote = False
            in_double_quote = False

    # 执行所有语句
    for statement in statements:
        if statement.strip():
            try:
                # 移除末尾的分号
                clean_statement = statement.rstrip(';').strip()
                cursor.execute(clean_statement)
                conn.commit()
                print(f"  [OK] 执行成功")
            except Exception as e:
                conn.rollback()
                # 如果是表已存在，忽略错误
                if "already exists" in str(e):
                    print(f"  [SKIP] 跳过（已存在）")
                else:
                    print(f"  [ERROR] 错误: {e}")

    cursor.close()


def main():
    """主函数"""
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误: DATABASE_URL 环境变量未设置")
        sys.exit(1)

    # 解析 DATABASE_URL
    # 格式: postgresql://user:password@host:port/database?sslmode=require
    db_url = database_url.replace("postgresql://", "")

    # 移除 sslmode 参数（psycopg2 会自动处理）
    if "?" in db_url:
        db_url = db_url.split("?")[0]

    parts = db_url.split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")

    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    database = host_db[1] if len(host_db) > 1 else "postgres"

    print(f"连接数据库: {host}:{port}/{database}")

    # 连接数据库
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode="require"
        )
        conn.autocommit = False
        print("数据库连接成功\n")
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

    # 获取迁移文件目录
    migrations_dir = Path(__file__).parent

    # 执行所有迁移
    migration_files = sorted(migrations_dir.glob("*.sql"))
    print(f"找到 {len(migration_files)} 个迁移文件\n")

    for migration_file in migration_files:
        if migration_file.name != "run_migrations.py":  # 跳过自己
            run_migration(conn, str(migration_file))
            print()

    conn.close()
    print("所有迁移完成！")


if __name__ == "__main__":
    main()
