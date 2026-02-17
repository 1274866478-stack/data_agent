# -*- coding: utf-8 -*-
"""
Data Validator - 数据验证层
================================

负责验证工具输出格式，检查数据完整性，在数据损坏时尝试修复。

核心功能:
    - JSON 格式验证
    - 数据完整性检查
    - 自动修复损坏的数据
    - 统一的错误格式

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
from typing import Any, Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# 数据验证常量
# ============================================================================

# 合法的数据工具返回格式
VALID_TOOL_FIELDS = {
    "execute_query": ["columns", "rows", "row_count", "success", "error", "error_type", "query"],
    "list_tables": ["tables", "table_count", "success", "error", "error_type"],
    "get_schema": ["table_name", "columns", "column_count", "success", "error", "error_type"],
}

# 必需的成功标记字段
SUCCESS_MARKERS = ["success", "row_count", "table_count", "column_count", "tables", "rows", "columns"]


# ============================================================================
# 数据验证类
# ============================================================================

class DataValidator:
    """
    数据验证器

    负责验证工具返回的数据格式是否正确，并在可能的情况下自动修复。
    """

    def __init__(self, auto_fix: bool = True):
        """
        初始化数据验证器

        Args:
            auto_fix: 是否自动修复可修复的问题
        """
        self.auto_fix = auto_fix
        self.validation_stats = {
            "total_validations": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "fixed_count": 0,
            "error_count": 0
        }

    def validate_tool_output(
        self,
        output: str,
        tool_name: str = "unknown"
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        验证工具输出

        Args:
            output: 工具输出的字符串（通常是 JSON）
            tool_name: 工具名称

        Returns:
            (is_valid, parsed_data, error_message) 元组
            - is_valid: 数据是否有效
            - parsed_data: 解析后的数据（如果有效）
            - error_message: 错误消息（如果无效）
        """
        self.validation_stats["total_validations"] += 1

        # 1. 尝试解析 JSON
        try:
            if isinstance(output, str):
                parsed = json.loads(output)
            else:
                parsed = output
        except json.JSONDecodeError as e:
            self.validation_stats["invalid_count"] += 1
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.warning(f"[DataValidator] {error_msg}")

            # 尝试修复 JSON
            if self.auto_fix:
                fixed = self._try_fix_json(output)
                if fixed is not None:
                    self.validation_stats["fixed_count"] += 1
                    return True, fixed, None

            return False, None, error_msg

        # 2. 验证数据结构
        is_valid, error_msg = self._validate_structure(parsed, tool_name)
        if is_valid:
            self.validation_stats["valid_count"] += 1
            return True, parsed, None
        else:
            self.validation_stats["invalid_count"] += 1
            logger.warning(f"[DataValidator] 结构验证失败: {error_msg}")

            # 尝试修复结构
            if self.auto_fix:
                fixed = self._try_fix_structure(parsed, tool_name)
                if fixed is not None:
                    self.validation_stats["fixed_count"] += 1
                    return True, fixed, None

            return False, parsed, error_msg

    def _validate_structure(self, data: Any, tool_name: str) -> Tuple[bool, Optional[str]]:
        """
        验证数据结构

        Args:
            data: 解析后的数据
            tool_name: 工具名称

        Returns:
            (is_valid, error_message) 元组
        """
        if not isinstance(data, dict):
            return False, f"期望字典格式，实际收到: {type(data).__name__}"

        # 检查是否是错误格式
        if "error" in data:
            # 错误格式也是有效的，只是表示执行失败
            if "error_type" in data:
                return True, None
            else:
                # 缺少 error_type，尝试添加
                if self.auto_fix:
                    data["error_type"] = "unknown_error"
                return True, None

        # 检查是否包含成功标记
        has_success_marker = any(marker in data for marker in SUCCESS_MARKERS)
        if not has_success_marker:
            return False, "缺少成功标记字段（success, row_count 等）"

        # 工具特定的验证
        if tool_name in VALID_TOOL_FIELDS:
            # 如果有 success 字段，必须是 True
            if "success" in data and data["success"] is False:
                # 这是一个明确的失败响应
                return True, None

        return True, None

    def _try_fix_json(self, output: str) -> Optional[Dict]:
        """
        尝试修复损坏的 JSON

        Args:
            output: 原始输出字符串

        Returns:
            修复后的数据，如果无法修复则返回 None
        """
        # 尝试常见的修复方法
        attempts = [
            self._fix_trailing_comma,
            self._fix_unquoted_keys,
            self._fix_escape_sequences,
        ]

        for fix_func in attempts:
            try:
                fixed = fix_func(output)
                if fixed:
                    parsed = json.loads(fixed)
                    logger.info(f"[DataValidator] 使用 {fix_func.__name__} 修复成功")
                    return parsed
            except:
                continue

        return None

    def _fix_trailing_comma(self, s: str) -> Optional[str]:
        """修复尾随逗号"""
        import re
        # 移除 ], } 前的逗号
        fixed = re.sub(r',(\s*[}\]])', r'\1', s)
        return fixed if fixed != s else None

    def _fix_unquoted_keys(self, s: str) -> Optional[str]:
        """修复未加引号的键"""
        import re
        # 这只是简单尝试，不能处理所有情况
        fixed = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', s)
        return fixed if fixed != s else None

    def _fix_escape_sequences(self, s: str) -> Optional[str]:
        """修复转义序列"""
        # 尝试修复常见的转义问题
        fixed = s.replace('\\n', '\\\\n').replace('\\t', '\\\\t')
        return fixed if fixed != s else None

    def _try_fix_structure(self, data: Dict, tool_name: str) -> Optional[Dict]:
        """
        尝试修复数据结构

        Args:
            data: 原始数据
            tool_name: 工具名称

        Returns:
            修复后的数据，如果无法修复则返回 None
        """
        if not isinstance(data, dict):
            return None

        # 添加缺失的必需字段
        if "success" not in data:
            # 如果有任何数据标记，设为成功
            if any(marker in data for marker in ["row_count", "table_count", "column_count", "rows", "columns", "tables"]):
                data["success"] = True

        # 如果有 rows 但没有 row_count
        if "rows" in data and "row_count" not in data:
            data["row_count"] = len(data["rows"])

        # 如果有 tables 但没有 table_count
        if "tables" in data and "table_count" not in data:
            data["table_count"] = len(data["tables"])

        # 如果有 columns 但没有 column_count
        if "columns" in data and "column_count" not in data:
            data["column_count"] = len(data["columns"])

        return data

    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return self.validation_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.validation_stats = {
            "total_validations": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "fixed_count": 0,
            "error_count": 0
        }


# ============================================================================
# 便捷函数
# ============================================================================

# 全局验证器实例
_global_validator: Optional[DataValidator] = None


def get_validator() -> DataValidator:
    """获取全局数据验证器实例"""
    global _global_validator
    if _global_validator is None:
        _global_validator = DataValidator()
    return _global_validator


def validate_tool_output(
    output: str,
    tool_name: str = "unknown"
) -> Tuple[bool, Any, Optional[str]]:
    """
    验证工具输出（便捷函数）

    Args:
        output: 工具输出
        tool_name: 工具名称

    Returns:
        (is_valid, parsed_data, error_message) 元组
    """
    return get_validator().validate_tool_output(output, tool_name)


def ensure_valid_output(
    output: str,
    tool_name: str = "unknown"
) -> str:
    """
    确保输出是有效的 JSON 字符串

    如果输出无效，返回标准错误格式。

    Args:
        output: 原始输出
        tool_name: 工具名称

    Returns:
        有效的 JSON 字符串
    """
    is_valid, parsed, error = validate_tool_output(output, tool_name)

    if is_valid and parsed is not None:
        if isinstance(parsed, str):
            return parsed
        return json.dumps(parsed, ensure_ascii=False)

    # 返回标准错误格式
    error_response = {
        "success": False,
        "error": error or "数据验证失败",
        "error_type": "validation_error",
        "tool_name": tool_name,
        "allow_llm_explain": True
    }
    return json.dumps(error_response, ensure_ascii=False)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Validator 测试")
    print("=" * 60)

    validator = DataValidator()

    # 测试 1: 有效的 JSON
    print("\n[TEST 1] 有效的 JSON")
    result = validator.validate_tool_output('{"success": true, "row_count": 0}', "execute_query")
    print(f"结果: {result}")

    # 测试 2: 损坏的 JSON
    print("\n[TEST 2] 损坏的 JSON（尾随逗号）")
    result = validator.validate_tool_output('{"success": true, "rows": [],}', "execute_query")
    print(f"结果: {result}")

    # 测试 3: 错误格式
    print("\n[TEST 3] 错误格式")
    result = validator.validate_tool_output('{"error": "表不存在", "error_type": "not_found"}', "execute_query")
    print(f"结果: {result}")

    # 测试 4: 统计信息
    print("\n[TEST 4] 统计信息")
    print(f"统计: {validator.get_stats()}")
