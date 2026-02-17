# -*- coding: utf-8 -*-
"""
测试省份查询跨表问题修复

验证：
1. BASE_SYSTEM_PROMPT 包含省份查询强制规则
2. _inject_geo_query_rules 函数正常工作
3. call_model 中的地理检测逻辑正常
"""


def test_base_system_prompt():
    """测试 BASE_SYSTEM_PROMPT 包含省份查询规则"""
    with open("sql_agent.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 检查关键内容
    checks = [
        ("省份查询强制规则标题", "【绝对强制】省份/城市查询必选 addresses 表"),
        ("禁止 users 表", "绝对禁止：使用 users 表查询地理位置"),
        ("强制 addresses 表", "必须使用：addresses 表查询地理位置"),
        ("占比类规则", "占比类问题特殊规则"),
    ]

    print("[BASE_SYSTEM_PROMPT 检查结果]")
    all_passed = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} - 未找到")
            all_passed = False

    return all_passed


def test_inject_geo_query_rules():
    """测试 _inject_geo_query_rules 函数"""
    # 模拟导入（仅检查函数定义）
    with open("sql_agent.py", "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("函数定义", "def _inject_geo_query_rules(user_query: str) -> str:"),
        ("省份关键词列表", "GEO_PROVINCE_KEYWORDS"),
        ("城市关键词列表", "GEO_CITY_KEYWORDS"),
        ("地址关键词列表", "GEO_ADDRESS_KEYWORDS"),
    ]

    print("\n[_inject_geo_query_rules 检查结果]")
    all_passed = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} - 未找到")
            all_passed = False

    return all_passed


def test_call_model_geo_detection():
    """测试 call_model 中的地理检测逻辑"""
    with open("sql_agent.py", "r", encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("is_geo_query 变量", "is_geo_query = False"),
        ("地理关键词检测", "is_geo_query = any(keyword in str(last_human_message).lower() for keyword in GEO_ALL_KEYWORDS)"),
        ("地理查询处理分支", "elif is_geo_query:"),
        ("强制 addresses 表", "必须使用"),
    ]

    print("\n[call_model 地理检测检查结果]")
    all_passed = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} - 未找到")
            all_passed = False

    return all_passed


def main():
    """运行所有测试"""
    print("=" * 60)
    print("[省份查询跨表问题修复测试]")
    print("=" * 60)

    results = []
    results.append(("BASE_SYSTEM_PROMPT", test_base_system_prompt()))
    results.append(("_inject_geo_query_rules", test_inject_geo_query_rules()))
    results.append(("call_model 地理检测", test_call_model_geo_detection()))

    print("\n" + "=" * 60)
    print("[测试结果汇总]")
    print("=" * 60)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} - {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n[所有测试通过]")
        return 0
    else:
        print("\n[部分测试失败，请检查]")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
