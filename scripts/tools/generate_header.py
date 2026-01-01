#!/usr/bin/env python3
"""
FractalFlow 文档头部生成工具

交互式收集文件元数据，根据模板生成文档头部并插入文件。
"""

import sys
from pathlib import Path


def get_template(file_ext: str) -> str:
    """根据文件扩展名获取对应的模板"""
    template_dir = Path(__file__).parent.parent / "templates"

    if file_ext == '.py':
        template_file = template_dir / "python_service.txt"
    elif file_ext in ['.ts', '.tsx']:
        template_file = template_dir / "typescript_component.txt"
    else:
        return None

    if template_file.exists():
        return template_file.read_text(encoding='utf-8')
    return None


def collect_metadata() -> dict:
    """交互式收集文件元数据"""
    metadata = {}

    print("\n=== FractalFlow 文档生成器 ===\n")

    metadata['module_name'] = input("模块名称 [MODULE_NAME]: ")
    metadata['description'] = input("简短描述: ")
    metadata['filename'] = input("文件名 [filename]: ")
    metadata['responsibility'] = input("职责描述: ")
    metadata['version'] = input("版本 [1.0.0]: ") or "1.0.0"

    return metadata


def fill_template(template: str, metadata: dict) -> str:
    """用收集的元数据填充模板"""
    header = template

    # 替换基本占位符
    header = header.replace('[MODULE_NAME]', metadata['module_name'])
    header = header.replace('[COMPONENT_NAME]', metadata['module_name'])
    header = header.replace('简短描述', metadata['description'])
    header = header.replace('filename.py', metadata['filename'])
    header = header.replace('filename.tsx', metadata['filename'])
    header = header.replace('核心职责描述', metadata['responsibility'])
    header = header.replace('1.0.0', metadata['version'])

    # 替换日期占位符（如果有的话）
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    header = header.replace('YYYY-MM-DD', today)

    return header


def insert_header(file_path: Path, header: str):
    """在文件开头插入文档头部"""
    # 读取原文件内容
    content = file_path.read_text(encoding='utf-8')

    # 检查是否已有文档头部
    has_header = False
    if file_path.suffix == '.py':
        has_header = content.startswith('"""')
    elif file_path.suffix in ['.ts', '.tsx']:
        has_header = content.startswith('/**')

    if has_header:
        print(f"\n警告: 文件似乎已有文档头部！")
        choice = input("是否覆盖？(y/N): ").lower()
        if choice != 'y':
            print("已取消操作")
            return

    # 插入新头部
    new_content = header + '\n' + content

    # 写回文件
    file_path.write_text(new_content, encoding='utf-8')
    print(f"\n✅ 成功为 {file_path.name} 添加 FractalFlow 文档头部")


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_header.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    # 获取模板
    template = get_template(file_path.suffix)
    if not template:
        print(f"错误: 不支持的文件类型: {file_path.suffix}")
        sys.exit(1)

    # 收集元数据
    metadata = collect_metadata()

    # 填充模板
    header = fill_template(template, metadata)

    # 插入文件
    insert_header(file_path, header)

    print("\n⚠️  请记住人工审核并补充以下内容：")
    print("   - [INPUT] 字段：输入参数/Props")
    print("   - [OUTPUT] 字段：输出/返回值")
    print("   - [LINK] 字段：上游/下游依赖（可使用 analyze_dependencies.py）")
    print("   - [POS]/[STATE] 字段：位置信息或组件状态")


if __name__ == '__main__':
    main()
