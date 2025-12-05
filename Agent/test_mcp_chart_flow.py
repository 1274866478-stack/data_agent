"""
测试 mcp-echarts 完整工作流程
直接调用 mcp-echarts 工具生成图表
"""
import asyncio
import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp import ClientSession
from mcp.client.sse import sse_client


async def test_generate_bar_chart():
    """测试直接调用 generate_bar_chart 工具"""
    
    print("=" * 60)
    print("📊 测试 mcp-echarts 柱状图生成")
    print("=" * 60)
    
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
        
        # 找到 generate_bar_chart 工具
        bar_tool = None
        for tool in tools:
            if tool.name == "generate_bar_chart":
                bar_tool = tool
                break
        
        if not bar_tool:
            print("❌ 未找到 generate_bar_chart 工具")
            return False
        
        print(f"\n✅ 找到工具: {bar_tool.name}")
        
        # 准备测试数据（模拟 SQL 查询结果转换后的格式）
        test_data = [
            {"category": "电子产品", "value": 45},
            {"category": "服装", "value": 30},
            {"category": "食品", "value": 25},
            {"category": "家居", "value": 18},
        ]
        
        print(f"\n📦 测试数据:")
        print(json.dumps(test_data, ensure_ascii=False, indent=2))
        
        # 调用工具
        print(f"\n🚀 调用 generate_bar_chart...")

        # 工具是 LangChain StructuredTool，使用 ainvoke 调用
        tool_input = {
            "title": "各分类产品数量统计",
            "data": test_data,
            "axisXTitle": "产品分类",
            "axisYTitle": "数量",
        }

        print(f"   工具输入: {json.dumps(tool_input, ensure_ascii=False)}")
        print(f"   工具类型: {type(bar_tool)}")
        print(f"   工具方法: {dir(bar_tool)[:15]}...")

        # 尝试不同的调用方式
        try:
            result = await bar_tool.ainvoke(tool_input)
            print(f"   ainvoke 结果: {result}")
        except Exception as e:
            print(f"   ainvoke 失败: {e}")
            result = None

        # 如果 ainvoke 失败，尝试 invoke
        if not result:
            try:
                result = bar_tool.invoke(tool_input)
                print(f"   invoke 结果: {result}")
            except Exception as e:
                print(f"   invoke 失败: {e}")
        
        print(f"\n📊 工具返回结果:")
        print(f"   类型: {type(result)}")
        print(f"   长度: {len(str(result)) if result else 0} 字符")

        if result:
            result_str = str(result)

            # 显示前200字符
            print(f"\n   前200字符:")
            print(f"   {result_str[:200]}")

            if len(result_str) > 200:
                print(f"\n   ... (共 {len(result_str)} 字符)")

            # 检查返回类型
            if result_str.startswith("data:image/png;base64,"):
                print("\n✅ 返回了 Base64 PNG 图片 (带 data URI 前缀)!")

                # 保存图片测试
                import base64
                import os
                base64_data = result_str.split(",", 1)[1]
                os.makedirs("./charts", exist_ok=True)
                with open("./charts/test_mcp_bar.png", "wb") as f:
                    f.write(base64.b64decode(base64_data))
                print("   已保存到: ./charts/test_mcp_bar.png")

            elif len(result_str) > 1000:
                # 尝试检测是否是纯 Base64
                try:
                    import base64
                    decoded = base64.b64decode(result_str[:100])
                    if decoded[:8] == b'\x89PNG\r\n\x1a\n':
                        print("\n✅ 返回了纯 Base64 PNG 图片数据!")

                        # 保存图片
                        import os
                        os.makedirs("./charts", exist_ok=True)
                        with open("./charts/test_mcp_bar.png", "wb") as f:
                            f.write(base64.b64decode(result_str))
                        print("   已保存到: ./charts/test_mcp_bar.png")
                except:
                    pass

            elif result_str.startswith("http"):
                print(f"\n✅ 返回了图片 URL!")
        else:
            print("   返回为空")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_raw_mcp_call():
    """使用原始 MCP 客户端测试"""
    print("\n" + "=" * 60)
    print("[RAW MCP] Testing raw MCP client")
    print("=" * 60)

    url = "http://localhost:3033/sse"

    test_data = [
        {"category": "Electronics", "value": 45},
        {"category": "Clothing", "value": 30},
        {"category": "Food", "value": 25},
    ]

    try:
        async with sse_client(url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()

                print(f"\n[OK] MCP session initialized")

                # 列出可用工具
                tools_result = await session.list_tools()
                print(f"   Tools count: {len(tools_result.tools)}")

                # 调用 generate_bar_chart
                result = await session.call_tool(
                    "generate_bar_chart",
                    {
                        "title": "Test Bar Chart",
                        "data": test_data,
                    }
                )

                print(f"\n[RESULT] call_tool returned:")
                print(f"   Type: {type(result)}")

                if hasattr(result, 'content'):
                    print(f"   Content items: {len(result.content)}")
                    for i, item in enumerate(result.content):
                        item_type = item.type if hasattr(item, 'type') else 'unknown'
                        print(f"   [{i}] type: {item_type}")

                        if hasattr(item, 'text'):
                            text = item.text
                            print(f"       text length: {len(text)}")
                            print(f"       text[:100]: {text[:100]}")

                        if hasattr(item, 'data'):
                            data = item.data
                            print(f"       data length: {len(data) if data else 0}")
                            if data:
                                print(f"       data[:100]: {data[:100]}")

                                # 保存图片
                                import base64
                                import os
                                os.makedirs("./charts", exist_ok=True)
                                with open("./charts/test_raw_mcp.png", "wb") as f:
                                    f.write(base64.b64decode(data))
                                print("       [SAVED] ./charts/test_raw_mcp.png")

                return True

    except Exception as e:
        print(f"[ERROR] Raw MCP call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n[START] Testing mcp-echarts chart generation\n")

    # 先测试原始 MCP 调用
    success1 = await test_raw_mcp_call()

    # 再测试 LangChain 包装
    # success2 = await test_generate_bar_chart()

    print("\n" + "=" * 60)
    print(f"[DONE] Raw MCP test: {'PASS' if success1 else 'FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

