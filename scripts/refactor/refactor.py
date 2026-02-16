#!/usr/bin/env python3
"""
主重构脚本 - 执行项目目录结构重构

使用方法:
    python scripts/refactor/refactor.py --dry-run     # 预览
    python scripts/refactor/refactor.py --execute      # 执行
"""

import os
import shutil
import json
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# 项目根目录
ROOT = Path(__file__).parent.parent.parent

# 新目录结构定义
NEW_STRUCTURE = {
    "apps": {
        "description": "应用层（前端 + 后端）",
        "subdirs": ["frontend", "backend"],
    },
    "services": {
        "description": "核心服务（AI Agent）",
        "subdirs": ["agent-v1", "agent-v2"],
    },
    "infrastructure": {
        "description": "基础设施",
        "subdirs": ["docker", "database", "storage"],
    },
    "tools": {
        "description": "工具和脚本",
        "subdirs": ["deployment", "development", "testing"],
    },
    "docs": {
        "description": "文档",
        "subdirs": ["architecture", "api", "user-guides", "qa"],
    },
    "config": {
        "description": "配置文件",
        "subdirs": [],
    },
    "metadata": {
        "description": "元数据和配置管理",
        "subdirs": ["agent", "bmad", "openspec", "github"],
    },
}

# 文件移动映射（简化版，主要目录映射）
MOVE_MAPPINGS = {
    # 应用层
    "frontend": "apps/frontend",
    "backend": "apps/backend",

    # 服务层
    "Agent": "services/agent-v1",
    "AgentV2": "services/agent-v2",

    # 基础设施
    "docker-compose.yml": "config/docker-compose.yml",
    ".env.example": "config/.env.example",
    "docker-compose.override.yml.example": "config/docker-compose.override.yml.example",
    ".mcp.json": "config/.mcp.json",

    # 工具（分类移动）
    "scripts/setup.sh": "tools/deployment/setup.sh",
    "scripts/docker-start.sh": "tools/deployment/docker-start.sh",
    "scripts/docker-stop.sh": "tools/deployment/docker-stop.sh",
    "scripts/validate-config.sh": "tools/deployment/validate-config.sh",
    "scripts/check-env-vars.py": "tools/development/check-env-vars.py",
    "scripts/security_audit.py": "tools/development/security_audit.py",
    "scripts/generate_test_database.py": "tools/testing/generate_test_database.py",
    "scripts/check-docker.py": "tools/development/check-docker.py",
    "scripts/check-ports.py": "tools/development/check-ports.py",

    # 数据存储
    "data_storage": "infrastructure/storage/data_storage",
    "backend/migrations": "infrastructure/database/migrations",
    "backend/scripts/init-db.sql": "infrastructure/database/init-db.sql",

    # 元数据
    ".agent": "metadata/agent/.agent",
    ".bmad-core": "metadata/bmad/.bmad-core",
    "openspec": "metadata/openspec/openspec",
    ".github": "metadata/github/.github",

    # 文档（保持原结构）
    "docs": "docs",
}

# 需要在原位置创建的符号链接（向后兼容）
SYMLINKS = {
    "frontend": "apps/frontend",
    "backend": "apps/backend",
    "Agent": "services/agent-v1",
    "AgentV2": "services/agent-v2",
}


class RefactorExecutor:
    """重构执行器"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = ROOT / f".backup_refactor_{self.timestamp}"
        self.log_file = ROOT / "scripts" / "refactor" / f"refactor_log_{self.timestamp}.txt"
        self.operations = []

    def log(self, message: str):
        """记录日志"""
        print(message)
        self.operations.append(message)

    def create_backup(self):
        """创建备份"""
        self.log(f"Creating backup at: {self.backup_dir}")

        if not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True)

            # 备份关键目录
            backup_items = ['frontend', 'backend', 'Agent', 'AgentV2', 'scripts']

            for item in backup_items:
                src = ROOT / item
                if src.exists():
                    dst = self.backup_dir / item
                    if not self.dry_run:
                        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                            'node_modules', '__pycache__', '.next', '*.pyc'
                        ))
                    self.log(f"  Backed up: {item}")

    def create_new_structure(self):
        """创建新目录结构"""
        self.log("Creating new directory structure...")

        for dir_name, config in NEW_STRUCTURE.items():
            dir_path = ROOT / dir_name

            if not dir_path.exists():
                self.log(f"  Creating: {dir_name}/")
                if not self.dry_run:
                    dir_path.mkdir(parents=True, exist_ok=True)

            # 创建子目录
            for subdir in config.get("subdirs", []):
                subdir_path = dir_path / subdir
                if not subdir_path.exists():
                    self.log(f"    Creating: {dir_name}/{subdir}/")
                    if not self.dry_run:
                        subdir_path.mkdir(parents=True, exist_ok=True)

    def move_files(self):
        """移动文件和目录"""
        self.log("Moving files and directories...")

        # 首先移动大目录
        big_dirs = ['frontend', 'backend', 'Agent', 'AgentV2']
        for dir_name in big_dirs:
            if dir_name in MOVE_MAPPINGS:
                src = ROOT / dir_name
                dst = ROOT / MOVE_MAPPINGS[dir_name]

                if src.exists() and not dst.exists():
                    self.log(f"  Moving: {dir_name} -> {MOVE_MAPPINGS[dir_name]}")
                    if not self.dry_run:
                        shutil.move(str(src), str(dst))

        # 然后移动其他文件和目录
        for src_name, dst_path in MOVE_MAPPINGS.items():
            if src_name in big_dirs:
                continue  # 已经处理过了

            src = ROOT / src_name
            dst = ROOT / dst_path

            if src.exists() and not dst.exists():
                # 确保目标目录存在
                dst.parent.mkdir(parents=True, exist_ok=True)

                self.log(f"  Moving: {src_name} -> {dst_path}")
                if not self.dry_run:
                    if src.is_dir():
                        shutil.move(str(src), str(dst))
                    else:
                        shutil.move(str(src), str(dst))

    def create_symlinks(self):
        """创建符号链接（向后兼容）"""
        if os.name == 'nt':  # Windows
            self.log("Skipping symlinks on Windows (use junctions instead)")
            return

        self.log("Creating compatibility symlinks...")

        for link_name, target in SYMLINKS.items():
            link_path = ROOT / link_name

            if not link_path.exists():
                self.log(f"  Creating symlink: {link_name} -> {target}")
                if not self.dry_run:
                    link_path.symlink_to(target)

    def update_gitignore(self):
        """更新 .gitignore 文件"""
        gitignore_path = ROOT / ".gitignore"

        if not gitignore_path.exists():
            return

        self.log("Updating .gitignore...")

        new_entries = [
            "# Refactor backups",
            ".backup_refactor_*/",
            "",
            "# Refactor metadata",
            "scripts/refactor/file_mappings.json",
            "scripts/refactor/refactor_log_*.txt",
        ]

        if not self.dry_run:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(new_entries))

    def save_log(self):
        """保存操作日志"""
        if not self.dry_run:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.operations))

    def execute(self):
        """执行重构"""
        mode = "DRY RUN" if self.dry_run else "EXECUTE"
        self.log(f"\n{'='*60}")
        self.log(f"Refactoring Project - {mode}")
        self.log(f"{'='*60}\n")

        # 步骤
        self.create_backup()
        self.create_new_structure()
        self.move_files()
        self.create_symlinks()
        self.update_gitignore()
        self.save_log()

        self.log(f"\n{'='*60}")
        self.log(f"Refactoring complete!")
        self.log(f"{'='*60}")

        if self.dry_run:
            self.log("\nThis was a DRY RUN. No changes were made.")
            self.log("Run with --execute to apply changes.")


def main():
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Refactor project directory structure"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the refactoring (default is dry-run)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup'
    )

    args = parser.parse_args()

    executor = RefactorExecutor(dry_run=not args.execute)

    try:
        executor.execute()
    except KeyboardInterrupt:
        print("\n\nRefactoring interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during refactoring: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
