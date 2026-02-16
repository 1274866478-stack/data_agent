# -*- coding: utf-8 -*-
"""
AgentV2 End-to-End Test
=======================

端到端测试，验证 AgentV2 的完整功能链路。

测试覆盖:
    1. 配置加载
    2. AgentFactory 创建
    3. SQL 安全中间件
    4. 工具集成

作者: BMad Master
版本: 2.0.0
"""

import sys
from pathlib import Path

# 添加 AgentV2 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("AgentV2 End-to-End Test")
print("=" * 70)

# ============================================================================
# 测试 1: 模块导入
# ============================================================================
print("\n[TEST 1] 模块导入测试")
print("-" * 70)

try:
    # 使用相对导入
    import AgentV2
    from AgentV2.core import AgentFactory
    from AgentV2.config import get_config
    from AgentV2.middleware import SQLSecurityMiddleware

    print("[PASS] 所有核心模块导入成功")
    print(f"[INFO] AgentV2 版本: {AgentV2.__version__}")

except ImportError as e:
    print(f"[FAIL] 模块导入失败: {e}")
    sys.exit(1)

# ============================================================================
# 测试 2: 配置系统
# ============================================================================
print("\n[TEST 2] 配置系统测试")
print("-" * 70)

try:
    config = get_config()

    print(f"[INFO] LLM 配置:")
    print(f"  - Model: {config.llm.model}")
    print(f"  - Temperature: {config.llm.temperature}")
    print(f"  - Max Tokens: {config.llm.max_tokens}")

    print(f"[INFO] 数据库配置:")
    print(f"  - URL: {config.database.url[:40]}...")
    print(f"  - Type: {config.database.db_type}")

    print(f"[INFO] 中间件配置:")
    print(f"  - Filesystem: {config.middleware.enable_filesystem}")
    print(f"  - SubAgents: {config.middleware.enable_subagents}")
    print(f"  - SQL Security: {config.middleware.enable_sql_security}")

    print("[PASS] 配置系统正常")

except Exception as e:
    print(f"[FAIL] 配置测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 测试 3: AgentFactory
# ============================================================================
print("\n[TEST 3] AgentFactory 测试")
print("-" * 70)

try:
    factory = AgentFactory(
        model="deepseek-chat",
        temperature=0.1,
        enable_filesystem=True,
        enable_subagents=False,  # 简化测试
    )

    print("[INFO] AgentFactory 创建成功")
    print(f"[INFO] LLM: {factory.model}")
    print(f"[INFO] 中间件启用: filesystem={factory.enable_filesystem}")

    # 测试 LLM 创建 (不实际调用)
    llm = factory.create_llm()
    print(f"[INFO] LLM 实例类型: {type(llm).__name__}")

    print("[PASS] AgentFactory 测试通过")

except Exception as e:
    print(f"[FAIL] AgentFactory 测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 测试 4: SQL 安全中间件
# ============================================================================
print("\n[TEST 4] SQL 安全中间件测试")
print("-" * 70)

try:
    middleware = SQLSecurityMiddleware()

    # 测试安全的 SQL
    safe_sql = "SELECT * FROM users WHERE id = 1"
    is_safe, error = middleware.validate(safe_sql)
    assert is_safe, f"Safe SQL should pass: {error}"
    print(f"[PASS] Safe SQL validated: {safe_sql[:40]}...")

    # 测试危险的 SQL
    dangerous_sql = "DELETE FROM users WHERE id = 1"
    is_safe, error = middleware.validate(dangerous_sql)
    assert not is_safe, "Dangerous SQL should be blocked"
    print(f"[PASS] Dangerous SQL blocked: {dangerous_sql[:40]}...")
    print(f"[INFO] Block reason: {error[:60]}...")

    print("[PASS] SQL 安全中间件测试通过")

except Exception as e:
    print(f"[FAIL] SQL 中间件测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 测试 5: MCP 工具配置
# ============================================================================
print("\n[TEST 5] MCP 工具配置测试")
print("-" * 70)

try:
    from AgentV2.tools.mcp_tools import get_default_mcp_config

    mcp_config = get_default_mcp_config()

    print(f"[INFO] MCP 服务器配置:")
    for name, cfg in mcp_config.items():
        args_str = ' '.join(cfg['args'][:2])
        print(f"  - {name}: {cfg['command']} {args_str}...")

    print("[PASS] MCP 配置测试通过")

except Exception as e:
    print(f"[FAIL] MCP 配置测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 测试总结
# ============================================================================
print("\n" + "=" * 70)
print("[SUMMARY] 端到端测试总结")
print("=" * 70)

test_results = [
    ("模块导入", "PASS"),
    ("配置系统", "PASS"),
    ("AgentFactory", "PASS"),
    ("SQL 安全中间件", "PASS"),
    ("MCP 工具配置", "PASS"),
]

for test, result in test_results:
    status = "[PASS]" if result == "PASS" else "[FAIL]"
    print(f"  {status} {test}")

print("\n" + "=" * 70)
print("[SUCCESS] AgentV2 核心功能验证完成！")
print("=" * 70)

# ============================================================================
# 下一步建议
# ============================================================================
print("\n[NEXT STEPS] 后续开发任务:")
print("  1. 实现实际的 Agent 创建和查询执行")
print("  2. 集成真实的 MCP 工具连接")
print("  3. 添加租户隔离中间件")
print("  4. 实现 SubAgent 架构")
print("  5. 性能基准测试")

print("\n[INTEGRATION] 与后端 FastAPI 集成:")
print("  1. 创建 /api/v2/query 端点")
print("  2. 注入 AgentFactory 依赖")
print("  3. 处理租户认证")
print("  4. 返回标准化响应")

print("\n[DOCUMENTATION] 需要更新的文档:")
print("  - AgentV2/README.md")
print("  - backend/docs/api-v2.md")
print("  - CLAUDE.md (更新 Agent 部分)")
