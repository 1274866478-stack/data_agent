# -*- coding: utf-8 -*-
"""
测试语义层工具功能
==================

验证新增的三个语义层工具：
1. list_schema_files - 列出语义层文档
2. read_schema_file - 读取语义层文档内容
3. search_schema - 搜索语义层文档

安全测试：
- 路径遍历攻击防护
- 内容大小限制
"""

import sys
import os
import json

# 添加路径
sys.path.insert(0, 'C:/data_agent')

from AgentV2.tools.database_tools import (
    list_schema_files,
    read_schema_file,
    search_schema,
    SchemaFSValidator
)


def test_list_schema_files():
    """测试 1: 列出语义层文档"""
    print("=" * 60)
    print("测试 1: list_schema_files()")
    print("=" * 60)

    result = list_schema_files()

    try:
        files = json.loads(result)
        print(f"[PASS] 成功找到 {len(files)} 个语义层文档：")
        for file_info in files:
            print(f"  - {file_info['filename']} ({file_info['size']} bytes)")
        return True
    except json.JSONDecodeError:
        print(f"[FAIL] 返回结果不是有效的 JSON: {result}")
        return False
    except Exception as e:
        print(f"[FAIL] 错误: {e}")
        return False


def test_read_schema_file():
    """测试 2: 读取语义层文档"""
    print("\n" + "=" * 60)
    print("测试 2: read_schema_file('Orders.yaml')")
    print("=" * 60)

    result = read_schema_file("Orders.yaml")

    if "错误：" in result:
        print(f"[FAIL] {result}")
        return False

    # 截断显示前 500 字符
    preview = result[:500] + "..." if len(result) > 500 else result
    print(f"[PASS] 成功读取 Orders.yaml (共 {len(result)} 字符)：")
    print(f"\n{preview}")
    return True


def test_read_schema_file_with_section():
    """测试 3: 读取语义层文档的特定部分"""
    print("\n" + "=" * 60)
    print("测试 3: read_schema_file('Orders.yaml', section='measures')")
    print("=" * 60)

    result = read_schema_file("Orders.yaml", section="measures")

    if "错误：" in result:
        print(f"[FAIL] {result}")
        return False

    print(f"[PASS] 成功读取 Orders.yaml 的 measures 部分 (共 {len(result)} 字符)：")
    print(f"\n{result}")
    return True


def test_search_schema():
    """测试 4: 搜索关键词"""
    print("\n" + "=" * 60)
    print("测试 4: search_schema('revenue')")
    print("=" * 60)

    result = search_schema("revenue")

    try:
        results = json.loads(result)
        if isinstance(results, str) and "未找到" in results:
            print(f"[WARN] {results}")
            return True
        elif isinstance(results, list):
            print(f"[PASS] 找到 {len(results)} 个匹配结果：")
            for match in results:
                print(f"  - 文件: {match['file']}")
                print(f"    匹配数: {len(match['matches'])}")
            return True
        else:
            print(f"[FAIL] 意外的返回类型: {type(result)}")
            return False
    except json.JSONDecodeError:
        print(f"[FAIL] 返回结果不是有效的 JSON: {result}")
        return False


def test_path_traversal_attack():
    """测试 5: 路径遍历攻击防护"""
    print("\n" + "=" * 60)
    print("测试 5: 安全测试 - 路径遍历攻击")
    print("=" * 60)

    # 尝试路径遍历攻击
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "C:/Windows/System32/config/SAM"
    ]

    all_safe = True
    for path in malicious_paths:
        result = read_schema_file(path)
        if "错误：不允许访问" in result or "错误：文件" in result:
            print(f"[PASS] 成功阻止路径遍历攻击: {path}")
        else:
            print(f"[FAIL] 安全漏洞！未阻止路径: {path}")
            all_safe = False

    return all_safe


def test_content_size_limit():
    """测试 6: 内容大小限制"""
    print("\n" + "=" * 60)
    print("测试 6: 内容大小限制")
    print("=" * 60)

    result = read_schema_file("Orders.yaml")

    # 检查是否被截断
    if len(result) > 5500:  # 允许一些容差
        print(f"[FAIL] 内容大小限制失效：返回 {len(result)} 字符")
        return False
    elif "(内容过长，已截断)" in result:
        print(f"[PASS] 内容被截断，共 {len(result)} 字符")
        return True
    else:
        print(f"[PASS] 内容在限制范围内，共 {len(result)} 字符")
        return True


def test_schema_validator():
    """测试 7: SchemaFSValidator 验证"""
    print("\n" + "=" * 60)
    print("测试 7: SchemaFSValidator 安全验证")
    print("=" * 60)

    # 测试合法路径
    base_path = SchemaFSValidator.ALLOWED_BASE_PATH
    print(f"基础路径: {base_path}")

    legal_path = base_path / "Orders.yaml"
    if SchemaFSValidator.validate_path(legal_path):
        print(f"[PASS] 合法路径验证通过: {legal_path}")
    else:
        print(f"[FAIL] 合法路径验证失败: {legal_path}")
        return False

    # 测试非法路径
    illegal_path = base_path / ".." / ".." / "etc" / "passwd"
    if not SchemaFSValidator.validate_path(illegal_path):
        print(f"[PASS] 非法路径被正确拒绝: {illegal_path}")
    else:
        print(f"[FAIL] 非法路径未被拒绝: {illegal_path}")
        return False

    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("语义层工具功能验证测试")
    print("=" * 60 + "\n")

    tests = [
        ("列出文档", test_list_schema_files),
        ("读取完整文件", test_read_schema_file),
        ("读取部分内容", test_read_schema_file_with_section),
        ("搜索关键词", test_search_schema),
        ("路径遍历防护", test_path_traversal_attack),
        ("内容大小限制", test_content_size_limit),
        ("路径验证器", test_schema_validator),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 抛出异常: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "[PASS] 通过" if result else "[FAIL] 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n[PASS] 所有测试通过！语义层工具已成功实施。")
    else:
        print(f"\n[FAIL] {total - passed} 个测试失败，请检查。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
