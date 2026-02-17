"""
省份简称智能匹配测试

测试场景：
1. 简称 "安徽" → 完整名称 "安徽省"
2. 城市查询 "深圳" → 映射到省份 "广东省"
3. 非省份列不受影响
4. 完整名称保持不变
"""

import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.database_tools import _expand_province_condition, PROVINCE_ALIAS_MAP


class TestProvinceMatching:
    """省份简称智能匹配测试"""

    def test_province_alias_expansion(self):
        """测试省份简称扩展"""
        # 简称应该扩展为完整名称
        result = _expand_province_condition("安徽", "province")
        assert "安徽" in result
        assert "安徽省" in result
        print(f"✓ '安徽' 扩展为: {result}")

    def test_full_province_name_unchanged(self):
        """测试完整省份名称保持不变"""
        result = _expand_province_condition("安徽省", "province")
        assert result == ["安徽省"]
        print(f"✓ '安徽省' 保持不变: {result}")

    def test_city_to_province_mapping(self):
        """测试城市到省份的映射"""
        result = _expand_province_condition("深圳", "province")
        assert "深圳" in result
        assert "广东省" in result
        print(f"✓ '深圳' 扩展为: {result}")

    def test_non_province_column(self):
        """测试非省份列不受影响"""
        result = _expand_province_condition("安徽", "name")
        assert result == ["安徽"]
        print(f"✓ 非省份列 'name' 保持不变: {result}")

    def test_all_provinces_covered(self):
        """测试所有省份都有映射"""
        common_provinces = ["安徽", "浙江", "江苏", "北京", "上海", "广东"]
        for province in common_provinces:
            result = _expand_province_condition(province, "province")
            assert len(result) >= 2  # 至少包含简称和完整名称
            print(f"✓ '{province}' → {result}")

    def test_province_alias_map_completeness(self):
        """测试省份映射表完整性"""
        # 检查常见省份
        required_mappings = {
            "安徽": "安徽省",
            "浙江": "浙江省",
            "江苏": "江苏省",
            "北京": "北京市",
            "上海": "上海市",
            "广东": "广东省",
        }

        for short, full in required_mappings.items():
            assert short in PROVINCE_ALIAS_MAP, f"缺少简称 '{short}' 的映射"
            assert PROVINCE_ALIAS_MAP[short] == full, f"'{short}' 应该映射到 '{full}'"

        print(f"✓ 省份映射表完整，包含 {len(PROVINCE_ALIAS_MAP)} 个映射")


def main():
    """运行测试"""
    print("=" * 60)
    print("省份简称智能匹配测试")
    print("=" * 60)

    test = TestProvinceMatching()

    tests = [
        ("省份简称扩展", test.test_province_alias_expansion),
        ("完整名称保持不变", test.test_full_province_name_unchanged),
        ("城市到省份映射", test.test_city_to_province_mapping),
        ("非省份列不受影响", test.test_non_province_column),
        ("所有省份覆盖", test.test_all_provinces_covered),
        ("映射表完整性", test.test_province_alias_map_completeness),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n测试: {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ 错误: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
