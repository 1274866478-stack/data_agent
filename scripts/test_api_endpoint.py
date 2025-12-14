#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 API 端点脚本
测试 /api/v1/query 端点的 Agent 集成功能
"""
import sys
import os
import asyncio
import json
from pathlib import Path
import requests
import time

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("="*60)
print("API 端点测试")
print("="*60)

# 配置
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/v1/query"

def test_api_health():
    """测试 API 健康状态"""
    print("\n[测试 1] 检查 API 服务是否运行...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"  [OK] API 服务正在运行")
            print(f"  - 响应: {response.json()}")
            return True
        else:
            print(f"  [WARNING] API 服务返回状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [X] 无法连接到 API 服务 ({API_BASE_URL})")
        print(f"  - 请确保后端服务已启动: cd backend && uvicorn src.app.main:app --reload")
        return False
    except Exception as e:
        print(f"  [X] 检查 API 服务时出错: {e}")
        return False

def test_query_endpoint():
    """测试查询端点"""
    print("\n[测试 2] 测试 /api/v1/query 端点...")
    
    # 测试请求数据
    test_request = {
        "query": "显示所有表",
        "connection_id": None,  # 如果没有连接ID，Agent会使用默认数据库
        "enable_cache": False,
        "force_refresh": True
    }
    
    print(f"  - 请求: {json.dumps(test_request, indent=2, ensure_ascii=False)}")
    
    try:
        # 发送请求
        print(f"  - 发送 POST 请求到 {API_ENDPOINT}...")
        start_time = time.time()
        response = requests.post(
            API_ENDPOINT,
            json=test_request,
            headers={
                "Content-Type": "application/json",
                # 如果需要认证，添加 Authorization header
            },
            timeout=60  # Agent 查询可能需要较长时间
        )
        elapsed_time = time.time() - start_time
        
        print(f"  - 响应状态码: {response.status_code}")
        print(f"  - 响应时间: {elapsed_time:.2f} 秒")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"  [OK] 查询成功")
            print(f"  - Query ID: {response_data.get('query_id', 'N/A')}")
            print(f"  - 生成的 SQL: {response_data.get('generated_sql', 'N/A')[:100]}...")
            print(f"  - 结果行数: {response_data.get('row_count', 0)}")
            print(f"  - 置信度: {response_data.get('confidence_score', 0)}")
            print(f"  - 解释: {response_data.get('explanation', 'N/A')[:100]}...")
            
            # 检查图表数据
            execution_result = response_data.get('execution_result')
            if execution_result:
                chart_type = execution_result.get('chart_type')
                chart_data = execution_result.get('chart_data')
                if chart_type and chart_type != 'table' and chart_type != 'none':
                    print(f"  - 图表类型: {chart_type}")
                    if chart_data:
                        if chart_data.startswith('data:'):
                            print(f"  - 图表数据: Base64 编码 (长度: {len(chart_data)} 字符)")
                        else:
                            print(f"  - 图表数据: URL ({chart_data})")
                    else:
                        print(f"  - 图表数据: 未生成")
            
            return True
        else:
            print(f"  [X] 查询失败")
            print(f"  - 错误响应: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  [X] 请求超时（超过 60 秒）")
        print(f"  - Agent 查询可能需要更长时间，请检查日志")
        return False
    except Exception as e:
        print(f"  [X] 测试查询端点时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    # 测试 1: 检查 API 服务
    if not test_api_health():
        print("\n" + "="*60)
        print("[FAILURE] API 服务未运行")
        print("="*60)
        print("\n请先启动后端服务:")
        print("  cd backend")
        print("  uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # 测试 2: 测试查询端点
    success = test_query_endpoint()
    
    print("\n" + "="*60)
    if success:
        print("[SUCCESS] API 端点测试完成")
    else:
        print("[FAILURE] API 端点测试失败")
    print("="*60)

if __name__ == "__main__":
    main()

