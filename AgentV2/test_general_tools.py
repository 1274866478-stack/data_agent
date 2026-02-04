# -*- coding: utf-8 -*-
"""
测试通用工具集成
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AgentV2.core.agent_factory_v2 import AgentFactory

def test_general_tools():
    """测试通用工具是否被正确添加到Agent"""

    print("=" * 60)
    print("测试通用工具集成")
    print("=" * 60)

    # 创建工厂
    factory = AgentFactory()

    # 构建工具（不传connection_id，使用默认）
    tools = factory._build_tools(
        connection_id=None,
        db_session=None,
        tenant_id="test_tenant"
    )

    print(f"\n总工具数: {len(tools)}")

    # 检查通用工具
    general_tool_names = [
        "get_date_range_info",
        "get_current_date",
        "get_current_time",
        "get_relative_date"
    ]

    print("\n检查通用工具:")
    tool_names = [t.name for t in tools]
    for name in general_tool_names:
        if name in tool_names:
            print(f"  ✅ {name} - 已添加")
        else:
            print(f"  ❌ {name} - 缺失")

    # 测试通用工具功能
    print("\n测试通用工具功能:")
    for tool in tools:
        if tool.name == "get_date_range_info":
            try:
                result = tool.invoke({})
                print(f"  get_date_range_info() 结果:")
                print(f"    {result}")
            except Exception as e:
                print(f"  ❌ 调用失败: {e}")
            break
    else:
        print("  ❌ 未找到 get_date_range_info 工具")

    print("\n所有工具列表:")
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool.name}: {tool.description[:60]}...")

if __name__ == "__main__":
    test_general_tools()
