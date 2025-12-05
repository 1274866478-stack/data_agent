"""
详细检查 mcp-echarts 工具的参数 Schema
"""
import asyncio
import json
from langchain_mcp_adapters.client import MultiServerMCPClient


async def inspect_tools():
    """获取所有工具的详细参数定义"""
    
    mcp_config = {
        "echarts": {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 60.0,
        }
    }
    
    print("=" * 70)
    print("📋 mcp-echarts 工具参数详细说明")
    print("=" * 70)
    
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    
    # 重点关注这几个常用工具
    priority_tools = [
        'generate_bar_chart',
        'generate_line_chart', 
        'generate_pie_chart',
        'generate_echarts'
    ]
    
    for tool in tools:
        if tool.name in priority_tools:
            print(f"\n{'='*70}")
            print(f"🔧 工具: {tool.name}")
            print(f"{'='*70}")
            print(f"\n📝 描述:\n{tool.description}\n")
            
            # 直接打印 args_schema (已经是 dict)
            if tool.args_schema:
                print("📦 参数 Schema:")
                print(json.dumps(tool.args_schema, indent=2, ensure_ascii=False))
            
            print("\n" + "-" * 70)
    
    # 显示所有工具列表
    print(f"\n\n{'='*70}")
    print("📊 所有可用工具列表")
    print("="*70)
    for i, tool in enumerate(tools, 1):
        print(f"  {i:2}. {tool.name}")


if __name__ == "__main__":
    asyncio.run(inspect_tools())

