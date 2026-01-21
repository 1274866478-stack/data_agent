"""
Phase 2 验证脚本 - 验证多智能体框架
"""

import sys
from pathlib import Path

# 添加 AgentV2 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "AgentV2"))


def test_imports():
    """测试所有 Agent 模块是否可以导入"""
    print("=== 测试模块导入 ===\n")

    tests = []

    # 测试 BaseAgent
    try:
        from subagents.base_agent import BaseAgent
        print("[OK] base_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] base_agent: {e}")
        tests.append(False)

    # 测试 RouterAgent
    try:
        from subagents.router_agent import RouterAgent
        print("[OK] router_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] router_agent: {e}")
        tests.append(False)

    # 测试 PlannerAgent
    try:
        from subagents.planner_agent import PlannerAgent
        print("[OK] planner_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] planner_agent: {e}")
        tests.append(False)

    # 测试 GeneratorAgent
    try:
        from subagents.generator_agent import GeneratorAgent
        print("[OK] generator_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] generator_agent: {e}")
        tests.append(False)

    # 测试 CriticAgent
    try:
        from subagents.critic_agent import CriticAgent
        print("[OK] critic_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] critic_agent: {e}")
        tests.append(False)

    # 测试 RepairAgent
    try:
        from subagents.repair_agent import RepairAgent
        print("[OK] repair_agent imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] repair_agent: {e}")
        tests.append(False)

    # 测试 Swarm Graph
    try:
        from graphs.swarm_graph import build_swarm_graph, ChatBiState
        print("[OK] swarm_graph imported")
        tests.append(True)
    except Exception as e:
        print(f"[FAIL] swarm_graph: {e}")
        tests.append(False)

    print(f"\n导入测试: {sum(tests)}/{len(tests)} 通过")
    return all(tests)


def test_yaml_configs():
    """测试 YAML 配置文件是否可以加载"""
    print("\n=== 测试配置文件 ===\n")

    import yaml

    tests = []

    # 测试业务规则
    try:
        with open("AgentV2/rules/business_rules.yaml", "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
            print(f"[OK] business_rules.yaml: {len(rules.get('rules', []))} 条规则")
            tests.append(True)
    except Exception as e:
        print(f"[FAIL] business_rules.yaml: {e}")
        tests.append(False)

    # 测试错误模式
    try:
        with open("self_healing/error_patterns.yaml", "r", encoding="utf-8") as f:
            patterns = yaml.safe_load(f)
            print(f"[OK] error_patterns.yaml: {len(patterns.get('patterns', []))} 种模式")
            tests.append(True)
    except Exception as e:
        print(f"[FAIL] error_patterns.yaml: {e}")
        tests.append(False)

    print(f"\n配置测试: {sum(tests)}/{len(tests)} 通过")
    return all(tests)


def test_graph_structure():
    """测试状态图结构"""
    print("\n=== 测试状态图结构 ===\n")

    try:
        from graphs.swarm_graph import build_swarm_graph

        # 构建图（不传 LLM）
        graph = build_swarm_graph(llm=None, cube_schema={})

        # 获取图的结构
        print(f"[OK] 图构建成功")
        print(f"     节点数: {len(graph.nodes)}")
        print(f"     节点: {list(graph.nodes.keys())}")

        return True
    except Exception as e:
        print(f"[FAIL] 图构建失败: {e}")
        return False


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    results = []
    results.append(test_imports())
    results.append(test_yaml_configs())
    results.append(test_graph_structure())

    print("\n" + "=" * 50)
    if all(results):
        print("Phase 2 验证: 全部通过")
    else:
        print("Phase 2 验证: 部分失败")
        sys.exit(1)
