"""
测试 mcp-echarts MCP 服务连接
运行前请确保已启动 mcp-echarts 服务：mcp-echarts -t sse -p 3033
"""
import asyncio
import sys


async def test_mcp_echarts_connection():
    """测试连接 mcp-echarts 服务并获取可用工具"""
    
    print("=" * 60)
    print("🔍 测试 mcp-echarts MCP 服务连接")
    print("=" * 60)
    
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("❌ 错误: 请安装 langchain-mcp-adapters")
        print("   pip install langchain-mcp-adapters")
        return False
    
    mcp_config = {
        "echarts": {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 60.0,
        }
    }
    
    print(f"\n📡 尝试连接: http://localhost:3033/sse")
    
    try:
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
        
        print(f"\n✅ 连接成功! 共获取到 {len(tools)} 个工具\n")
        print("-" * 60)
        
        for i, tool in enumerate(tools, 1):
            print(f"\n🔧 工具 {i}: {tool.name}")
            print(f"   描述: {tool.description[:80]}..." if len(tool.description) > 80 else f"   描述: {tool.description}")
            
            # 显示参数信息
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema = tool.args_schema
                if hasattr(schema, 'schema'):
                    props = schema.schema().get('properties', {})
                    required = schema.schema().get('required', [])
                    if props:
                        print(f"   参数:")
                        for param_name, param_info in props.items():
                            req_mark = "*" if param_name in required else ""
                            param_type = param_info.get('type', 'any')
                            print(f"      - {param_name}{req_mark}: {param_type}")
        
        print("\n" + "=" * 60)
        print("✅ mcp-echarts 服务运行正常!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n💡 请检查:")
        print("   1. mcp-echarts 服务是否已启动")
        print("   2. 运行: mcp-echarts -t sse -p 3033")
        print("   3. 端口 3033 是否被占用")
        return False


async def test_generate_chart():
    """测试生成一个简单图表"""
    
    print("\n" + "=" * 60)
    print("🎨 测试生成图表")
    print("=" * 60)
    
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    mcp_config = {
        "echarts": {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 120.0,
        }
    }
    
    try:
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
        
        # 找到 generate_bar_chart 或 generate_echarts 工具
        bar_tool = None
        for tool in tools:
            if 'bar' in tool.name.lower():
                bar_tool = tool
                break
        
        if bar_tool:
            print(f"\n📊 找到柱状图工具: {bar_tool.name}")
            print(f"   准备调用测试...")
            # 这里只是验证工具存在，实际调用需要通过 LLM
            print("   ✅ 工具可用，可以通过 LLM 调用")
        else:
            print("⚠️ 未找到柱状图工具")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("\n开始测试 mcp-echarts 服务...\n")
    
    success = asyncio.run(test_mcp_echarts_connection())
    
    if success and len(sys.argv) > 1 and sys.argv[1] == '--chart':
        asyncio.run(test_generate_chart())

