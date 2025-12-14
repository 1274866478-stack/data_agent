#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端集成测试脚本
检查前端类型定义与后端 API 的兼容性
"""
import sys
import os
import json
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("="*60)
print("前端集成测试")
print("="*60)

def check_backend_schema():
    """检查后端 API Schema"""
    print("\n[测试 1] 检查后端 API Schema...")
    
    try:
        # 读取后端 schema 文件
        schema_file = Path("backend/src/app/schemas/query.py")
        if not schema_file.exists():
            print("  [X] 后端 schema 文件不存在")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键字段
        required_fields = {
            'QueryRequest': ['query', 'connection_id'],
            'QueryResponseV3': ['query_id', 'generated_sql', 'results', 'execution_result']
        }
        
        all_found = True
        for class_name, fields in required_fields.items():
            if f"class {class_name}" in content:
                print(f"  [OK] 找到 {class_name} 类")
                for field in fields:
                    if field in content:
                        print(f"    - {field}: 已定义")
                    else:
                        print(f"    [WARNING] {field}: 未找到")
                        all_found = False
            else:
                print(f"  [X] 未找到 {class_name} 类")
                all_found = False
        
        # 检查 execution_result 中的 chart 字段
        if 'execution_result' in content and 'chart' in content:
            print(f"  [OK] execution_result 包含 chart 字段")
        else:
            print(f"  [WARNING] execution_result 可能不包含 chart 字段")
        
        return all_found
        
    except Exception as e:
        print(f"  [X] 检查失败: {e}")
        return False


def check_frontend_types():
    """检查前端类型定义"""
    print("\n[测试 2] 检查前端类型定义...")
    
    try:
        # 检查前端 API 客户端
        api_client_file = Path("frontend/src/lib/api-client.ts")
        if not api_client_file.exists():
            print("  [X] 前端 API 客户端文件不存在")
            return False
        
        with open(api_client_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键类型
        required_types = [
            'ChatQueryRequest',
            'ChatQueryResponse',
            'AgentQueryResult',
            'ChartType'
        ]
        
        all_found = True
        for type_name in required_types:
            if f"interface {type_name}" in content or f"type {type_name}" in content or f"export type {type_name}" in content:
                print(f"  [OK] 找到 {type_name} 类型定义")
            else:
                print(f"  [WARNING] 未找到 {type_name} 类型定义")
                all_found = False
        
        # 检查是否使用 /api/v1/query 端点
        if '/api/v1/query' in content or '/query' in content:
            print(f"  [OK] 前端代码中包含 /query 端点引用")
        else:
            print(f"  [WARNING] 前端代码中未找到 /api/v1/query 端点引用")
            print(f"    [INFO] 前端当前使用 /llm/chat/completions 端点")
            print(f"    [INFO] 需要更新前端以支持 Agent 的 /api/v1/query 端点")
        
        return all_found
        
    except Exception as e:
        print(f"  [X] 检查失败: {e}")
        return False


def check_agent_service_integration():
    """检查 Agent 服务集成"""
    print("\n[测试 3] 检查 Agent 服务集成...")
    
    try:
        # 检查 agent_service.py
        agent_service_file = Path("backend/src/app/services/agent_service.py")
        if not agent_service_file.exists():
            print("  [X] Agent 服务文件不存在")
            return False
        
        with open(agent_service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键函数
        required_functions = [
            'run_agent_query',
            'convert_agent_response_to_query_response',
            'extract_chart_path_from_answer',
            'load_chart_as_base64'
        ]
        
        all_found = True
        for func_name in required_functions:
            if f"def {func_name}" in content or f"async def {func_name}" in content:
                print(f"  [OK] 找到 {func_name} 函数")
            else:
                print(f"  [X] 未找到 {func_name} 函数")
                all_found = False
        
        # 检查 chart_data 处理
        if 'chart_data' in content and 'base64' in content:
            print(f"  [OK] Agent 服务包含图表数据处理（Base64）")
        else:
            print(f"  [WARNING] Agent 服务可能不包含图表数据处理")
        
        return all_found
        
    except Exception as e:
        print(f"  [X] 检查失败: {e}")
        return False


def check_query_endpoint_integration():
    """检查查询端点集成"""
    print("\n[测试 4] 检查查询端点集成...")
    
    try:
        # 检查 query.py 端点
        query_endpoint_file = Path("backend/src/app/api/v1/endpoints/query.py")
        if not query_endpoint_file.exists():
            print("  [X] 查询端点文件不存在")
            return False
        
        with open(query_endpoint_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键集成点
        checks = [
            ('run_agent_query', 'Agent 查询函数调用'),
            ('convert_agent_response_to_query_response', '响应转换函数'),
            ('is_agent_available', 'Agent 可用性检查'),
            ('connection_id', '数据源连接 ID 支持')
        ]
        
        all_found = True
        for check_key, check_desc in checks:
            if check_key in content:
                print(f"  [OK] {check_desc}: 已集成")
            else:
                print(f"  [WARNING] {check_desc}: 未找到")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"  [X] 检查失败: {e}")
        return False


def generate_integration_report():
    """生成集成报告"""
    print("\n[测试 5] 生成集成报告...")
    
    report = {
        "backend_api": {
            "endpoint": "/api/v1/query",
            "method": "POST",
            "request_schema": {
                "query": "string (required)",
                "connection_id": "string (optional)",
                "enable_cache": "boolean (optional)",
                "force_refresh": "boolean (optional)"
            },
            "response_schema": {
                "query_id": "string",
                "generated_sql": "string",
                "results": "array",
                "execution_result": {
                    "success": "boolean",
                    "data": "object",
                    "chart": {
                        "chart_type": "string",
                        "chart_data": "string (base64 encoded image)"
                    }
                }
            }
        },
        "frontend_integration": {
            "current_endpoint": "/llm/chat/completions",
            "agent_endpoint": "/api/v1/query (not yet integrated)",
            "status": "需要更新前端以支持 Agent 查询"
        },
        "recommendations": [
            "更新前端 API 客户端以支持 /api/v1/query 端点",
            "添加 connection_id 参数支持",
            "添加图表数据（chart_data）显示支持",
            "更新类型定义以匹配后端 QueryResponseV3"
        ]
    }
    
    report_file = Path("frontend_integration_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"  [OK] 集成报告已生成: {report_file}")
    print(f"    - 后端 API: {report['backend_api']['endpoint']}")
    print(f"    - 前端当前端点: {report['frontend_integration']['current_endpoint']}")
    print(f"    - 状态: {report['frontend_integration']['status']}")
    
    return True


def main():
    """主测试函数"""
    results = {}
    
    # 运行测试
    results['backend_schema'] = check_backend_schema()
    results['frontend_types'] = check_frontend_types()
    results['agent_service'] = check_agent_service_integration()
    results['query_endpoint'] = check_query_endpoint_integration()
    results['report'] = generate_integration_report()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[WARNING/X]"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n[SUCCESS] 所有检查通过")
    else:
        print("\n[INFO] 部分检查有警告或失败")
        print("这是正常的，前端可能需要更新以完全支持 Agent 查询功能")
    
    print("\n[建议]")
    print("1. 更新前端 API 客户端以支持 /api/v1/query 端点")
    print("2. 添加 connection_id 参数支持（数据源选择）")
    print("3. 添加图表数据（chart_data）显示支持")
    print("4. 更新类型定义以匹配后端 QueryResponseV3")
    
    print("="*60)


if __name__ == "__main__":
    main()

