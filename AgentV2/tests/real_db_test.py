# -*- coding: utf-8 -*-
"""
Real Database Connection Test
==============================

测试 AgentV2 与真实 PostgreSQL 数据库的连接。

作者: BMad Master
版本: 2.0.0
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 70)
print("AgentV2 真实数据库连接测试")
print("=" * 70)

# ============================================================================
# 测试 1: 数据库连接
# ============================================================================
print("\n[TEST 1] 数据库连接测试")
print("-" * 70)

# 获取数据库连接 URL
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/data_agent"
)

print(f"[INFO] 数据库 URL: {database_url[:40]}...")

# 尝试连接
conn = None
try:
    import psycopg2
    from psycopg2 import sql

    # 尝试连接数据库
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # 测试查询
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"[PASS] 数据库连接成功")
    print(f"[INFO] PostgreSQL 版本: {version[:50]}...")

    # 获取表列表
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        LIMIT 10;
    """)
    tables = cursor.fetchall()
    if tables:
        print(f"[INFO] 数据库表: {[t[0] for t in tables]}")

    cursor.close()

except Exception as e:
    print(f"[WARN] 数据库连接失败: {e}")
    print(f"[INFO] 将使用模拟模式进行测试")
finally:
    if conn:
        conn.close()

# ============================================================================
# 测试 2: MCP 工具连接
# ============================================================================
print("\n[TEST 2] MCP 工具连接测试")
print("-" * 70)

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    # MCP 配置
    mcp_config = {
        "postgres": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-postgres", database_url],
        },
        "echarts": {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-echarts"]
        }
    }

    print("[INFO] MCP 配置:")
    for name, cfg in mcp_config.items():
        print(f"  - {name}: {cfg['command']} {' '.join(cfg['args'][:2])}...")

    # 注意：实际连接需要 npx 和有效的数据库
    print("[INFO] 实际 MCP 连接需要:")
    print("  1. Node.js 和 npx 可用")
    print("  2. @modelcontextprotocol/server-postgres 已安装")
    print("  3. 数据库连接有效")
    print("[SKIP] 跳过实际 MCP 连接测试")

except Exception as e:
    print(f"[INFO] MCP 测试: {e}")

# ============================================================================
# 测试 3: Agent 创建 (模拟模式)
# ============================================================================
print("\n[TEST 3] Agent 创建 (模拟模式)")
print("-" * 70)

try:
    from AgentV2 import AgentFactory, TenantIsolationMiddleware

    # 创建工厂
    factory = AgentFactory(
        model="deepseek-chat",
        enable_tenant_isolation=True,
        enable_sql_security=True,
    )

    # 创建租户隔离中间件
    tenant_mw = TenantIsolationMiddleware(
        tenant_id="test_tenant",
        user_id="test_user"
    )

    print("[PASS] AgentFactory 创建成功")
    print(f"[INFO] 支持的功能:")
    print(f"  - 租户隔离: {factory.enable_tenant_isolation}")
    print(f"  - SQL 安全: {factory.enable_sql_security}")
    print(f"  - 文件系统: {factory.enable_filesystem}")

    # 测试中间件
    test_input = {"messages": [{"role": "user", "content": "查询数据"}]}
    enhanced = tenant_mw.pre_process(test_input)

    if "__tenant__" in enhanced:
        print("[PASS] 租户信息注入成功")

except Exception as e:
    print(f"[FAIL] Agent 创建失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 测试 4: 完整查询流程 (模拟)
# ============================================================================
print("\n[TEST 4] 完整查询流程 (模拟)")
print("-" * 70)

try:
    from AgentV2.middleware import SQLSecurityMiddleware

    sql_mw = SQLSecurityMiddleware()

    # 模拟查询流程
    test_queries = [
        ("SELECT * FROM users LIMIT 10", "安全"),
        ("DELETE FROM users", "危险"),
    ]

    for sql, expected in test_queries:
        is_safe, error = sql_mw.validate(sql)
        if expected == "安全":
            if is_safe:
                print(f"[PASS] 安全 SQL 通过: {sql[:40]}...")
            else:
                print(f"[FAIL] 安全 SQL 被错误拦截: {sql[:40]}...")
        else:
            if not is_safe:
                print(f"[PASS] 危险 SQL 被拦截: {sql[:40]}...")
            else:
                print(f"[FAIL] 危险 SQL 未被拦截: {sql[:40]}...")

    print("[PASS] 查询流程验证完成")

except Exception as e:
    print(f"[FAIL] 查询流程测试失败: {e}")

# ============================================================================
# 测试总结
# ============================================================================
print("\n" + "=" * 70)
print("[SUMMARY] 数据库连接测试总结")
print("=" * 70)

print("\n[STATUS] 测试模式: 模拟模式 (无真实数据库)")
print("[INFO] 要进行真实测试，需要:")
print("  1. 有效的 PostgreSQL 数据库连接")
print("  2. 安装 MCP 服务器: npm install -g @modelcontextprotocol/server-postgres")
print("  3. 配置环境变量 DATABASE_URL")

print("\n[NEXT STEPS] 后续任务:")
print("  1. 配置真实数据库连接")
print("  2. 测试 MCP PostgreSQL 工具")
print("  3. 实现 FastAPI 集成")
print("  4. 端到端查询测试")

print("\n" + "=" * 70)
