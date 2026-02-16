#!/usr/bin/env python3
"""
路径更新脚本 - 更新 import 语句和配置文件中的路径引用
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import json

# 项目根目录
ROOT = Path(__file__).parent.parent.parent

# 路径替换规则（旧路径 -> 新路径）
PATH_REPLACEMENTS = {
    # Python import 路径
    "Agent.": "services.agent_v1.",
    "AgentV2.": "services.agent_v2.",

    # Docker compose 中的路径
    "./frontend": "./apps/frontend",
    "./backend": "./apps/backend",
    "./Agent": "./services/agent-v1",
    "./AgentV2": "./services/agent-v2",
    "./scripts": "./tools/deployment",
    "./data_storage": "./infrastructure/storage",

    # Python 中的模块路径
    "/Agent": "/services/agent-v1",
    "/AgentV2": "/services/agent-v2",
}

# 文件扩展名白名单
TEXT_FILE_EXTENSIONS = {
    '.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yaml', '.yml',
    '.md', '.txt', '.sh', '.bat', '.sql', '.env', '.example',
    '.dockerfile', '.toml', '.ini', '.cfg', '.conf'
}

# 需要特殊处理的文件模式
SPECIAL_FILE_PATTERNS = {
    'docker-compose*.yml': 'docker_compose',
    '*requirements*.txt': 'requirements',
    'package.json': 'package_json',
    '*.config.js': 'config_js',
    'tsconfig.json': 'tsconfig',
}

def is_text_file(file_path: Path) -> bool:
    """判断是否是文本文件"""
    # 检查扩展名
    if file_path.suffix.lower() in TEXT_FILE_EXTENSIONS:
        return True

    # 检查特殊文件名
    for pattern in SPECIAL_FILE_PATTERNS.keys():
        if file_path.match(pattern):
            return True

    return False

def update_python_imports(content: str, file_path: Path) -> Tuple[str, int]:
    """更新 Python 文件中的 import 语句"""
    original_content = content
    changes = 0

    # 更新 from Agent import ... 语句
    content = re.sub(
        r'from Agent([.\s])',
        r'from services.agent_v1\1',
        content
    )

    # 更新 from AgentV2 import ... 语句
    content = re.sub(
        r'from AgentV2([.\s])',
        r'from services.agent_v2\1',
        content
    )

    # 更新 import Agent 语句
    content = re.sub(
        r'\bimport Agent([.\s])',
        r'import services.agent_v1 as Agent\1',
        content
    )

    # 更新 import AgentV2 语句
    content = re.sub(
        r'\bimport AgentV2([.\s])',
        r'import services.agent_v2 as AgentV2\1',
        content
    )

    # 更新 sys.path 中的路径
    content = re.sub(
        r"sys\.path\.append\(['\"]\/Agent['\"]",
        r"sys.path.append(['/services/agent-v1",
        content
    )

    content = re.sub(
        r"sys\.path\.append\(['\"]\/AgentV2['\"]",
        r"sys.path.append(['/services/agent-v2",
        content
    )

    # 更新 PYTHONPATH 环境变量
    content = re.sub(
        r'PYTHONPATH=\/app:\/',
        r'PYTHONPATH=/app:/services/agent-v1:/services/agent-v2',
        content
    )

    if content != original_content:
        changes = len(original_content.split('\n')) - len(content.split('\n'))
        if changes == 0:
            changes = 1  # 至少有一个变化

    return content, changes

def update_typescript_imports(content: str, file_path: Path) -> Tuple[str, int]:
    """更新 TypeScript/JavaScript 文件中的 import 语句"""
    changes = 0

    # 这里可以添加 TypeScript 特定的路径更新逻辑
    # 例如更新 @/ 路径别名等

    return content, changes

def update_docker_compose(content: str, file_path: Path) -> Tuple[str, int]:
    """更新 docker-compose.yml 文件"""
    original_content = content

    # 更新所有路径引用
    for old_path, new_path in PATH_REPLACEMENTS.items():
        if old_path.startswith('./'):
            content = content.replace(old_path, new_path)

    # 更新 volume 挂载路径
    content = re.sub(
        r'\-\s+\.\/Agent:',
        r'- ./services/agent-v1:',
        content
    )

    content = re.sub(
        r'\-\s+\.\/AgentV2:',
        r'- ./services/agent-v2:',
        content
    )

    # 更改 context 路径
    content = re.sub(
        r'context:\s+\.\/frontend',
        r'context: ./apps/frontend',
        content
    )

    content = re.sub(
        r'context:\s+\.\/backend',
        r'context: ./apps/backend',
        content
    )

    changes = 1 if content != original_content else 0
    return content, changes

def update_config_file(content: str, file_path: Path) -> Tuple[str, int]:
    """更新配置文件"""
    original_content = content

    # 更新 .env 文件中的路径
    if '.env' in file_path.name:
        for old_path, new_path in PATH_REPLACEMENTS.items():
            content = content.replace(old_path, new_path)

    changes = 1 if content != original_content else 0
    return content, changes

def process_file(file_path: Path, dry_run: bool = True) -> Dict:
    """处理单个文件"""
    result = {
        'file': str(file_path.relative_to(ROOT)),
        'changes': 0,
        'status': 'skipped'
    }

    if not is_text_file(file_path):
        return result

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 根据文件类型选择处理方式
        if file_path.suffix == '.py':
            content, changes = update_python_imports(content, file_path)
        elif file_path.suffix in ['.ts', '.tsx', '.js', '.jsx']:
            content, changes = update_typescript_imports(content, file_path)
        elif 'docker-compose' in file_path.name:
            content, changes = update_docker_compose(content, file_path)
        elif '.env' in file_path.name or file_path.name.endswith('.example'):
            content, changes = update_config_file(content, file_path)
        else:
            content, changes = update_config_file(content, file_path)

        if changes > 0:
            result['changes'] = changes
            result['status'] = 'updated'

            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        else:
            result['status'] = 'no_changes'

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)

    return result

def scan_and_update(dry_run: bool = True) -> List[Dict]:
    """扫描并更新所有文件"""
    results = []

    # 扫描所有需要更新的目录
    scan_dirs = [
        ROOT / 'apps',
        ROOT / 'services',
        ROOT / 'infrastructure',
        ROOT / 'tools',
        ROOT / 'config',
        ROOT / 'metadata',
    ]

    # 也扫描根目录的配置文件
    config_files = [
        'docker-compose.yml',
        '.env.example',
        'package.json',
    ]

    for config_file in config_files:
        file_path = ROOT / config_file
        if file_path.exists():
            result = process_file(file_path, dry_run)
            results.append(result)

    # 扫描子目录
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        for file_path in scan_dir.rglob('*'):
            if file_path.is_file():
                result = process_file(file_path, dry_run)
                if result['status'] != 'skipped':
                    results.append(result)

    return results

def main():
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Scanning files for path updates...")

    results = scan_and_update(dry_run=True)

    # 统计结果
    updated = sum(1 for r in results if r['status'] == 'updated')
    no_changes = sum(1 for r in results if r['status'] == 'no_changes')
    errors = sum(1 for r in results if r['status'] == 'error')

    print(f"\nResults:")
    print(f"  Updated: {updated} files")
    print(f"  No changes: {no_changes} files")
    print(f"  Errors: {errors} files")

    if errors > 0:
        print("\nErrors:")
        for r in results:
            if r['status'] == 'error':
                print(f"  {r['file']}: {r.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
