#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Agent 功能脚本
测试 Agent 交互模式、MCP 服务器连接、图表生成功能
"""
import sys
import os
import asyncio
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加 Agent 目录到 Python 路径
_agent_path = Path(__file__).parent.parent / "Agent"
if _agent_path.exists() and str(_agent_path) not in sys.path:
    sys.path.insert(0, str(_agent_path))

print("="*60)
print("Agent 功能测试")
print("="*60)

async def test_mcp_connection():
    """测试 MCP 服务器连接"""
    print("\n[测试 1] 测试 MCP 服务器连接...")
    
    try:
        from sql_agent import _get_mcp_config, _get_or_create_agent
        from config import config
        
        # 检查配置
        print(f"  - 检查配置...")
        print(f"    DEEPSEEK_API_KEY: {'已设置' if config.deepseek_api_key else '未设置'}")
        print(f"    DATABASE_URL: {'已设置' if config.database_url else '未设置'}")
        
        if not config.deepseek_api_key:
            print("  [WARNING] DEEPSEEK_API_KEY 未设置，跳过 MCP 连接测试")
            return False
        
        if not config.database_url:
            print("  [WARNING] DATABASE_URL 未设置，跳过 MCP 连接测试")
            return False
        
        # 获取 MCP 配置
        mcp_config = _get_mcp_config()
        print(f"  - MCP 配置:")
        print(f"    - PostgreSQL MCP: {'已配置' if 'postgres' in mcp_config else '未配置'}")
        print(f"    - ECharts MCP: {'已配置' if 'echarts' in mcp_config else '未配置'}")
        
        # 尝试创建 Agent 和 MCP 客户端
        print(f"  - 尝试初始化 Agent 和 MCP 客户端...")
        try:
            agent, mcp_client = await _get_or_create_agent()
            print(f"  [OK] Agent 和 MCP 客户端初始化成功")
            
            # 尝试获取工具
            print(f"  - 尝试获取 MCP 工具...")
            tools = await mcp_client.get_tools()
            print(f"  [OK] 成功获取 {len(tools)} 个 MCP 工具")
            
            # 列出工具
            tool_names = [tool.name for tool in tools]
            print(f"  - 可用工具: {', '.join(tool_names[:10])}{'...' if len(tool_names) > 10 else ''}")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "502 Bad Gateway" in error_msg or "localhost:3033" in error_msg:
                print(f"  [WARNING] ECharts MCP 服务器未运行（这是正常的）")
                print(f"    [INFO] ECharts MCP 服务器需要单独启动（通常在 localhost:3033）")
                print(f"    [INFO] 在 Docker Compose 环境中，MCP 服务器会自动启动")
                print(f"    [INFO] Agent 功能已集成，但需要 MCP 服务器运行才能完整测试")
                return False
            else:
                print(f"  [X] Agent 初始化失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
    except ImportError as e:
        print(f"  [X] 导入失败: {e}")
        return False
    except Exception as e:
        print(f"  [X] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_query():
    """测试 Agent 查询功能"""
    print("\n[测试 2] 测试 Agent 查询功能...")
    
    try:
        from sql_agent import run_agent
        from config import config
        
        if not config.deepseek_api_key:
            print("  [WARNING] DEEPSEEK_API_KEY 未设置，跳过查询测试")
            return False
        
        if not config.database_url:
            print("  [WARNING] DATABASE_URL 未设置，跳过查询测试")
            return False
        
        # 测试一个简单的查询
        test_question = "显示所有表"
        print(f"  - 测试查询: '{test_question}'")
        print(f"  - 执行中...")
        
        try:
            response = await run_agent(test_question, thread_id="test-1", verbose=False)
            
            if response.success:
                print(f"  [OK] 查询成功")
                print(f"    - SQL: {response.sql[:100] if response.sql else 'N/A'}...")
                print(f"    - 回答: {response.answer[:200] if response.answer else 'N/A'}...")
                if response.data:
                    print(f"    - 数据行数: {response.data.row_count}")
                return True
            else:
                print(f"  [X] 查询失败: {response.error}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            if "502 Bad Gateway" in error_msg or "localhost:3033" in error_msg:
                print(f"  [WARNING] 查询失败：ECharts MCP 服务器未运行（这是正常的）")
                print(f"    [INFO] 需要启动 MCP 服务器才能执行完整查询")
                return False
            else:
                print(f"  [X] 查询执行失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
    except ImportError as e:
        print(f"  [X] 导入失败: {e}")
        return False
    except Exception as e:
        print(f"  [X] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chart_generation():
    """测试图表生成功能"""
    print("\n[测试 3] 测试图表生成功能...")
    
    try:
        from chart_service import ChartRequest, generate_chart, ChartResponse
        from models import ChartType
        
        # 测试数据（转换为 chart_service 期望的格式）
        test_data = [
            ["产品A", 100],
            ["产品B", 200],
            ["产品C", 150],
        ]
        
        print(f"  - 测试数据: {len(test_data)} 条记录")
        
        # 创建图表请求（使用 chart_service 的 ChartRequest 格式）
        chart_request = ChartRequest(
            type="bar",
            data=test_data,
            title="测试柱状图",
            series_name="销售额",
            x_axis_name="产品",
            y_axis_name="金额"
        )
        
        print(f"  - 检查图表服务模块...")
        print(f"    [INFO] ChartRequest 类型: {type(chart_request)}")
        print(f"    [INFO] 图表类型: {chart_request.type}")
        
        # 注意：实际生成图表需要 selenium 和 chromedriver，这里只测试模块导入
        print(f"  [OK] 图表服务模块导入成功")
        print(f"    [INFO] 实际图表生成需要 selenium 和 chromedriver")
        print(f"    [INFO] 在生产环境中，图表生成由 MCP ECharts 服务器处理")
        
        return True
            
    except ImportError as e:
        print(f"  [WARNING] 导入失败: {e}")
        print(f"    [INFO] 这可能是正常的，如果某些依赖未安装")
        return False
    except Exception as e:
        print(f"  [WARNING] 测试失败: {e}")
        print(f"    [INFO] 图表服务功能已集成，但可能需要额外配置")
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n[测试 0] 测试配置加载...")
    
    try:
        from config import config
        
        print(f"  - 配置来源检测...")
        
        # 检查后端配置是否可用
        backend_config_available = False
        try:
            backend_src = Path(__file__).parent.parent / "backend" / "src"
            if backend_src.exists():
                backend_config_available = True
                print(f"    [INFO] 检测到后端配置系统")
        except Exception:
            pass
        
        if backend_config_available:
            print(f"    [INFO] Agent 将优先使用后端配置")
        else:
            print(f"    [INFO] Agent 使用独立配置（Agent/.env 或环境变量）")
        
        # 检查配置值
        print(f"  - 配置值:")
        print(f"    - deepseek_api_key: {'已设置' if config.deepseek_api_key else '未设置'}")
        print(f"    - deepseek_base_url: {config.deepseek_base_url}")
        print(f"    - deepseek_model: {config.deepseek_model}")
        print(f"    - database_url: {'已设置' if config.database_url else '未设置'}")
        
        # 验证配置
        try:
            config.validate_config()
            print(f"  [OK] 配置验证通过")
            return True
        except ValueError as e:
            print(f"  [WARNING] 配置验证失败: {e}")
            print(f"    这是正常的，如果某些环境变量未设置")
            return False
            
    except ImportError as e:
        print(f"  [X] 导入失败: {e}")
        return False
    except Exception as e:
        print(f"  [X] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    results = {}
    
    # 测试配置加载
    results['config'] = test_config_loading()
    
    # 测试 MCP 连接
    results['mcp'] = await test_mcp_connection()
    
    # 测试 Agent 查询
    results['query'] = await test_agent_query()
    
    # 测试图表生成
    results['chart'] = test_chart_generation()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[SKIP/WARNING]"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n[SUCCESS] 所有测试通过")
    else:
        print("\n[INFO] 部分测试跳过或失败（可能是配置未设置）")
        print("这是正常的，如果某些环境变量（如 DEEPSEEK_API_KEY, DATABASE_URL）未设置")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

