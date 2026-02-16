#!/usr/bin/env python3
"""
项目重构分析脚本
分析当前目录结构，生成文件移动映射表
"""

import os
from pathlib import Path
from typing import Dict, List
import json

# 项目根目录
ROOT = Path(__file__).parent.parent.parent

# 新旧路径映射规则
MAPPING_RULES = {
    # 应用层
    "apps/frontend": "frontend",
    "apps/backend": "backend",

    # 服务层（AI Agent）
    "services/agent-v1": "Agent",
    "services/agent-v2": "AgentV2",

    # 基础设施
    "infrastructure/docker": ".",
    "infrastructure/database/init": "backend/scripts",
    "infrastructure/storage": "data_storage",

    # 工具
    "tools/deployment": "scripts",
    "tools/development": "scripts",
    "tools/testing": "scripts",

    # 文档
    "docs": "docs",

    # 元数据
    "metadata/config": ".",
    "metadata/agent": ".agent",
    "metadata/bmad": ".bmad-core",
    "metadata/openspec": "openspec",
}

def analyze_current_structure() -> Dict[str, List[str]]:
    """分析当前项目结构"""
    structure = {
        "apps": [],
        "services": [],
        "infrastructure": [],
        "tools": [],
        "docs": [],
        "metadata": [],
        "config": [],
    }

    # 分析主要目录
    for item in ROOT.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if item.name in ['frontend', 'backend']:
                structure["apps"].append(item.name)
            elif item.name.startswith('Agent'):
                structure["services"].append(item.name)
            elif item.name in ['scripts']:
                structure["tools"].append(item.name)
            elif item.name == 'docs':
                structure["docs"].append(item.name)

    # 分析隐藏目录
    for item in ROOT.iterdir():
        if item.is_dir() and item.name.startswith('.'):
            if item.name in ['.agent', '.bmad-core', 'openspec']:
                structure["metadata"].append(item.name)

    return structure

def generate_file_mappings() -> Dict[str, str]:
    """生成文件移动映射表"""
    mappings = {}

    # Frontend -> apps/frontend
    if (ROOT / "frontend").exists():
        for file_path in (ROOT / "frontend").rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(ROOT)
                new_path = Path("apps/frontend") / rel_path
                mappings[str(rel_path)] = str(new_path)

    # Backend -> apps/backend
    if (ROOT / "backend").exists():
        for file_path in (ROOT / "backend").rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(ROOT)
                new_path = Path("apps/backend") / rel_path
                mappings[str(rel_path)] = str(new_path)

    # Agent -> services/agent-v1
    if (ROOT / "Agent").exists():
        for file_path in (ROOT / "Agent").rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(ROOT)
                new_path = Path("services/agent-v1") / rel_path
                mappings[str(rel_path)] = str(new_path)

    # AgentV2 -> services/agent-v2
    if (ROOT / "AgentV2").exists():
        for file_path in (ROOT / "AgentV2").rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(ROOT)
                new_path = Path("services/agent-v2") / rel_path
                mappings[str(rel_path)] = str(new_path)

    # Scripts -> tools (分类移动)
    script_categories = {
        "setup.sh": "deployment",
        "docker-start.sh": "deployment",
        "validate-config.sh": "deployment",
        "check-env-vars.py": "development",
        "security_audit.py": "development",
        "generate_test_database.py": "testing",
        "check-docker.py": "development",
        "check-ports.py": "development",
    }

    if (ROOT / "scripts").exists():
        for file_path in (ROOT / "scripts").iterdir():
            if file_path.is_file():
                category = script_categories.get(file_path.name, "deployment")
                rel_path = file_path.relative_to(ROOT)
                new_path = Path(f"tools/{category}") / file_path.name
                mappings[str(rel_path)] = str(new_path)

    # Config files -> config/
    config_files = [
        ".env.example",
        ".mcp.json",
        "docker-compose.yml",
        "docker-compose.override.yml.example",
    ]

    for config_file in config_files:
        if (ROOT / config_file).exists():
            mappings[config_file] = f"config/{config_file}"

    # Metadata
    metadata_dirs = {
        ".agent": "metadata/agent",
        ".bmad-core": "metadata/bmad",
        "openspec": "metadata/openspec",
        ".github": "metadata/github",
    }

    for old_path, new_path in metadata_dirs.items():
        if (ROOT / old_path).exists():
            for file_path in (ROOT / old_path).rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(ROOT)
                    mappings[str(rel_path)] = f"{new_path}/{rel_path.relative_to(old_path)}"

    return mappings

def save_mappings(mappings: Dict[str, str]):
    """保存映射表到JSON文件"""
    output_file = ROOT / "scripts" / "refactor" / "file_mappings.json"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)

    print(f"✅ 映射表已保存到: {output_file}")
    print(f"   共 {len(mappings)} 个文件需要移动")

    # 生成分类统计
    stats = {}
    for old_path in mappings.keys():
        category = old_path.split('/')[0]
        stats[category] = stats.get(category, 0) + 1

    print("\n📊 移动统计:")
    for category, count in sorted(stats.items()):
        print(f"   {category}: {count} 个文件")

if __name__ == "__main__":
    import sys
    import io

    # 设置标准输出编码为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Analyzing project structure...")
    structure = analyze_current_structure()

    print("\nCurrent structure:")
    for category, items in structure.items():
        if items:
            print(f"   {category}: {', '.join(items)}")

    print("\nGenerating file mapping table...")
    mappings = generate_file_mappings()

    print("\nSaving mappings...")
    save_mappings(mappings)

    print("\nAnalysis complete!")
