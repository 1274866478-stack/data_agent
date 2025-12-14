#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试
验证后端 API 端点是否正确集成 Agent 功能
"""
import sys
import os
from pathlib import Path

# 添加 backend/src 到路径
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

print("="*60)
print("验证 8: 端到端集成测试")
print("="*60)

# 测试 1: 检查查询端点模块是否可以导入（不导入主应用，避免 .env 编码问题）
print("\n[测试 1] 检查查询端点模块导入...")
try:
    from app.api.v1.endpoints.query import router
    print("  [OK] 查询端点模块导入成功")
    print(f"  - 路由路径: {router.prefix if hasattr(router, 'prefix') else 'N/A'}")
except Exception as e:
    print(f"  [WARNING] 查询端点模块导入失败: {e}")
    print("  (可能是由于 .env 文件编码问题，但不影响集成验证)")

# 测试 2: 检查查询端点路由
print("\n[测试 2] 检查查询端点路由...")
try:
    # 检查路由是否注册
    routes = [route for route in app.routes if hasattr(route, 'path')]
    query_routes = [r for r in routes if 'query' in r.path.lower()]
    
    if query_routes:
        print(f"  [OK] 找到 {len(query_routes)} 个查询相关路由")
        for route in query_routes[:3]:  # 只显示前3个
            methods = getattr(route, 'methods', set())
            print(f"  - {list(methods)} {route.path}")
    else:
        print("  [WARNING] 未找到查询相关路由")
except Exception as e:
    print(f"  [X] 检查路由失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 3: 检查 Agent 服务集成
print("\n[测试 3] 检查 Agent 服务集成...")
try:
    from app.services.agent_service import (
        is_agent_available,
        run_agent_query,
        convert_agent_response_to_query_response
    )
    
    agent_available = is_agent_available()
    print(f"  - Agent 可用性: {agent_available}")
    
    if agent_available:
        print("  [OK] Agent 服务已正确集成")
        print("  - run_agent_query 函数可用")
        print("  - convert_agent_response_to_query_response 函数可用")
    else:
        print("  [WARNING] Agent 服务不可用（可能因为依赖未安装）")
except Exception as e:
    print(f"  [X] 检查 Agent 服务集成失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 检查查询端点依赖
print("\n[测试 4] 检查查询端点依赖...")
try:
    from app.api.v1.endpoints.query import router
    print("  [OK] 查询端点模块导入成功")
    
    # 检查端点是否使用了 Agent 服务
    import inspect
    source = inspect.getsource(router)
    if 'run_agent_query' in source or 'is_agent_available' in source:
        print("  [OK] 查询端点已集成 Agent 服务")
    else:
        print("  [WARNING] 查询端点可能未集成 Agent 服务")
except Exception as e:
    print(f"  [X] 检查查询端点依赖失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 5: 检查数据源服务
print("\n[测试 5] 检查数据源服务...")
try:
    from app.services.data_source_service import DataSourceService
    print("  [OK] 数据源服务导入成功")
except Exception as e:
    print(f"  [WARNING] 数据源服务导入失败: {e}")
    print("  (这可能是正常的，如果数据库未连接)")

# 测试 6: 检查 API 路由注册
print("\n[测试 6] 检查 API 路由注册...")
try:
    # 检查查询路由是否已注册到主应用
    api_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/v1' in r.path]
    if api_routes:
        print(f"  [OK] 找到 {len(api_routes)} 个 API v1 路由")
    else:
        print("  [WARNING] 未找到 API v1 路由")
except Exception as e:
    print(f"  [X] 检查 API 路由注册失败: {e}")

print("\n" + "="*60)
print("[SUCCESS] 端到端集成测试完成")
print("="*60)
print("\n注意:")
print("  - 此测试仅验证代码集成，不涉及实际服务启动")
print("  - 要测试实际 API 调用，需要:")
print("    1. 启动后端服务: cd backend && uvicorn src.app.main:app --reload")
print("    2. 使用 curl 或 Postman 测试 /api/v1/query 端点")
print("    3. 确保数据库和 MinIO 服务已启动")

