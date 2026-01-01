#!/usr/bin/env python3
"""
FractalFlow 依赖关系分析工具

自动分析 Python 和 TypeScript 文件的导入依赖关系，
生成 [LINK] 字段的初稿。
"""

import ast
import sys
import re
from pathlib import Path
from typing import List, Tuple


def analyze_python_imports(file_path: Path) -> List[str]:
    """分析 Python 文件的导入语句"""
    imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
    except Exception as e:
        print(f"错误: 无法解析文件 {file_path}: {e}", file=sys.stderr)

    return imports


def analyze_ts_imports(file_path: Path) -> List[str]:
    """分析 TypeScript 文件的导入语句"""
    imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配各种 import 语句
        patterns = [
            r'import\s+.*?\s+from\s+["\']([^"\']+)["\']',
            r'import\s*\(\s*["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)
    except Exception as e:
        print(f"错误: 无法解析文件 {file_path}: {e}", file=sys.stderr)

    return imports


def generate_link_section(file_path: Path, imports: List[str]) -> str:
    """生成 [LINK] 字段内容"""
    upstream = []

    for imp in imports:
        # 转换模块路径到相对文件路径
        if imp.startswith('src.app.'):
            rel_path = imp.replace('src.app.', '').replace('.', '/') + '.py'
            upstream.append(f"- [{rel_path}]({rel_path}) - 自动分析")
        elif imp.startswith('@/'):
            rel_path = imp.replace('@/', 'src/')
            upstream.append(f"- [{rel_path}]({rel_path}) - 自动分析")
        elif not imp.startswith(('react', 'next', 'lodash', 'clsx', 'zod')):
            # 其他非标准库导入
            upstream.append(f"- [{imp}]({imp}) - 自动分析")

    if not upstream:
        upstream = ["- 无"]

    return f"""## [LINK]
**上游依赖** (已读取源码):
{chr(10).join(upstream)}

**下游依赖**:
- 待补充

**调用方**:
- 待补充"""


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_dependencies.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    # 根据文件扩展名选择分析器
    if file_path.suffix == '.py':
        imports = analyze_python_imports(file_path)
    elif file_path.suffix in ['.ts', '.tsx']:
        imports = analyze_ts_imports(file_path)
    else:
        print(f"错误: 不支持的文件类型: {file_path.suffix}")
        sys.exit(1)

    # 生成并输出 [LINK] 字段
    link_section = generate_link_section(file_path, imports)

    print(f"\n# {file_path.name} 依赖分析结果\n")
    print(link_section)
    print("\n注意: 这是自动生成的初稿，请人工审核和补充！")


if __name__ == '__main__':
    main()
