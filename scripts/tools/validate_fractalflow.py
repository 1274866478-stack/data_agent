#!/usr/bin/env python3
"""
FractalFlow 规范验证工具

检查文件是否符合 FractalFlow 标准化文档规范，
包括字段完整性、路径有效性等。
"""

import sys
import re
from pathlib import Path
from typing import List, Dict


class FractalFlowValidator:
    """FractalFlow 文档验证器"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.errors = []
        self.warnings = []
        self.file_ext = file_path.suffix

    def validate(self):
        """执行完整验证"""
        content = self._read_file()

        if not self._has_header(content):
            self.errors.append("缺少文档头部")
            return False

        # 根据文件类型验证
        if self.file_ext == '.py':
            self._validate_python(content)
        elif self.file_ext in ['.ts', '.tsx']:
            self._validate_typescript(content)

        return len(self.errors) == 0

    def _read_file(self) -> str:
        """读取文件内容"""
        try:
            return self.file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.errors.append(f"无法读取文件: {e}")
            return ""

    def _has_header(self, content: str) -> bool:
        """检查是否有文档头部"""
        if self.file_ext == '.py':
            return content.startswith('"""')
        elif self.file_ext in ['.ts', '.tsx']:
            return content.startswith('/**')
        return False

    def _validate_python(self, content: str):
        """验证 Python 文件文档"""
        required_fields = [
            r'## \[HEADER\]',
            r'## \[INPUT\]',
            r'## \[OUTPUT\]',
            r'## \[LINK\]',
            r'## \[POS\]',
        ]

        for field in required_fields:
            if not re.search(field, content):
                self.errors.append(f"缺少必需字段: {field}")

        # 检查文件名
        if not re.search(r'\*\*文件名\*\*:.+', content):
            self.warnings.append("文件名字段为空")

        # 检查职责
        if not re.search(r'\*\*职责\*\*:.+', content):
            self.warnings.append("职责字段为空")

    def _validate_typescript(self, content: str):
        """验证 TypeScript 文件文档"""
        required_fields = [
            r'## \[MODULE\]',
            r'## \[INPUT\]',
            r'## \[OUTPUT\]',
            r'## \[LINK\]',
            r'## \[STATE\]',
            r'## \[SIDE-EFFECTS\]',
        ]

        for field in required_fields:
            if not re.search(field, content):
                self.errors.append(f"缺少必需字段: {field}")

        # 检查 Props 说明
        has_props = re.search(r'- \*\*[\w]+\*\*:.+', content)
        if not has_props:
            self.warnings.append("未找到 Props 参数说明")

    def report(self) -> Dict:
        """生成验证报告"""
        return {
            'file': str(self.file_path),
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
        }


def validate_file(file_path: Path) -> Dict:
    """验证单个文件"""
    validator = FractalFlowValidator(file_path)
    is_valid = validator.validate()
    return validator.report()


def main():
    if len(sys.argv) < 2:
        print("用法: python validate_fractalflow.py <file_path>")
        print("       python validate_fractalflow.py --all")
        sys.exit(1)

    if sys.argv[1] == '--all':
        # 验证所有相关文件
        print("验证所有文件...\n")

        files = []
        # 添加需要验证的文件列表
        for pattern in ['backend/**/*.py', 'frontend/src/**/*.{ts,tsx}']:
            files.extend(Path('.').glob(pattern))

        total = len(files)
        valid = 0

        for file_path in files:
            report = validate_file(file_path)
            if report['valid']:
                valid += 1
            else:
                print(f"❌ {report['file']}")
                for error in report['errors']:
                    print(f"   错误: {error}")
                for warning in report['warnings']:
                    print(f"   警告: {warning}")

        print(f"\n总计: {total} 个文件")
        print(f"✅ 合规: {valid} 个")
        print(f"❌ 不合规: {total - valid} 个")

    else:
        # 验证单个文件
        file_path = Path(sys.argv[1])

        if not file_path.exists():
            print(f"错误: 文件不存在: {file_path}")
            sys.exit(1)

        report = validate_file(file_path)

        print(f"\n验证结果: {file_path.name}\n")

        if report['valid']:
            print("✅ 文件符合 FractalFlow 规范")
        else:
            print("❌ 文件不符合 FractalFlow 规范\n")
            print("错误:")
            for error in report['errors']:
                print(f"  - {error}")

        if report['warnings']:
            print("\n警告:")
            for warning in report['warnings']:
                print(f"  - {warning}")

        sys.exit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
