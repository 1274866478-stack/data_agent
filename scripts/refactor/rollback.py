#!/usr/bin/env python3
"""
回滚脚本 - 将项目恢复到重构前的状态

使用方法:
    python scripts/refactor/rollback.py
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
ROOT = Path(__file__).parent.parent.parent


class RollbackExecutor:
    """回滚执行器"""

    def __init__(self, backup_dir: Path = None):
        if backup_dir is None:
            # 查找最新的备份目录
            backup_dirs = list(ROOT.glob(".backup_refactor_*"))
            if not backup_dirs:
                raise FileNotFoundError("No backup directories found")
            backup_dirs.sort(reverse=True)
            self.backup_dir = backup_dirs[0]
        else:
            self.backup_dir = backup_dir

        self.operations = []
        self.dry_run = False

    def log(self, message: str):
        """记录日志"""
        print(message)
        self.operations.append(message)

    def verify_backup(self):
        """验证备份完整性"""
        self.log(f"Verifying backup at: {self.backup_dir}")

        if not self.backup_dir.exists():
            raise FileNotFoundError(f"Backup directory not found: {self.backup_dir}")

        required_dirs = ['frontend', 'backend', 'Agent', 'AgentV2']
        for dir_name in required_dirs:
            backup_item = self.backup_dir / dir_name
            if not backup_item.exists():
                self.log(f"  WARNING: {dir_name} not found in backup")

        self.log("Backup verification complete")

    def remove_new_structure(self):
        """移除新的目录结构"""
        self.log("Removing new directory structure...")

        # 删除新结构中的目录
        new_dirs = [
            "apps/frontend",
            "apps/backend",
            "services/agent-v1",
            "services/agent-v2",
            "services",
            "apps",
            "infrastructure",
            "tools/deployment",
            "tools/development",
            "tools/testing",
            "tools",
            "config",
            "metadata",
        ]

        for dir_path in new_dirs:
            full_path = ROOT / dir_path
            if full_path.exists():
                self.log(f"  Removing: {dir_path}")
                if not self.dry_run:
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        full_path.unlink()

    def restore_from_backup(self):
        """从备份恢复"""
        self.log("Restoring from backup...")

        # 恢复主要目录
        restore_dirs = ['frontend', 'backend', 'Agent', 'AgentV2']

        for dir_name in restore_dirs:
            backup_item = self.backup_dir / dir_name
            target_item = ROOT / dir_name

            if backup_item.exists():
                # 删除现有的同名目录
                if target_item.exists():
                    self.log(f"  Removing existing: {dir_name}")
                    if not self.dry_run:
                        shutil.rmtree(target_item)

                # 恢复备份
                self.log(f"  Restoring: {dir_name}")
                if not self.dry_run:
                    shutil.copytree(backup_item, target_item)

    def restore_config_files(self):
        """恢复配置文件"""
        self.log("Restoring configuration files...")

        config_files = [
            "config/docker-compose.yml",
            "config/.env.example",
        ]

        for config_file in config_files:
            backup_file = self.backup_dir / config_file.split('/')[-1]
            target_file = ROOT / config_file

            if backup_file.exists():
                # 恢复到根目录
                root_target = ROOT / backup_file.name
                self.log(f"  Restoring: {backup_file.name} -> {root_target}")
                if not self.dry_run:
                    shutil.copy2(backup_file, root_target)

            # 删除 config 目录中的文件
            if target_file.exists():
                self.log(f"  Removing: {config_file}")
                if not self.dry_run:
                    target_file.unlink()

        # 删除空的 config 目录
        config_dir = ROOT / "config"
        if config_dir.exists() and not list(config_dir.iterdir()):
            self.log("  Removing empty: config/")
            if not self.dry_run:
                config_dir.rmdir()

    def remove_symlinks(self):
        """移除符号链接"""
        if os.name == 'nt':  # Windows
            return

        self.log("Removing compatibility symlinks...")

        potential_symlinks = ['frontend', 'backend', 'Agent', 'AgentV2']

        for link_name in potential_symlinks:
            link_path = ROOT / link_name
            if link_path.is_symlink():
                self.log(f"  Removing symlink: {link_name}")
                if not self.dry_run:
                    link_path.unlink()

    def cleanup_refactor_artifacts(self):
        """清理重构产生的文件"""
        self.log("Cleaning up refactor artifacts...")

        artifacts = [
            "scripts/refactor/file_mappings.json",
            "scripts/refactor/refactor_log_*.txt",
        ]

        for pattern in artifacts:
            if '*' in pattern:
                for file_path in ROOT.glob(pattern):
                    self.log(f"  Removing: {file_path.relative_to(ROOT)}")
                    if not self.dry_run:
                        file_path.unlink()
            else:
                file_path = ROOT / pattern
                if file_path.exists():
                    self.log(f"  Removing: {pattern}")
                    if not self.dry_run:
                        file_path.unlink()

    def execute(self):
        """执行回滚"""
        print(f"\n{'='*60}")
        print(f"Rollback to: {self.backup_dir.name}")
        print(f"{'='*60}\n")

        self.verify_backup()
        self.remove_new_structure()
        self.restore_from_backup()
        self.restore_config_files()
        self.remove_symlinks()
        self.cleanup_refactor_artifacts()

        print(f"\n{'='*60}")
        print(f"Rollback complete!")
        print(f"{'='*60}")

        # 询问是否删除备份
        response = input(f"\nDelete backup directory '{self.backup_dir}'? (yes/no): ")
        if response.lower() == 'yes':
            shutil.rmtree(self.backup_dir)
            print(f"Deleted: {self.backup_dir}")


def main():
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Rollback project refactoring"
    )
    parser.add_argument(
        '--backup',
        type=str,
        help='Specify backup directory (default: latest)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without executing'
    )

    args = parser.parse_args()

    try:
        backup_dir = Path(args.backup) if args.backup else None
        executor = RollbackExecutor(backup_dir)
        executor.dry_run = args.dry_run
        executor.execute()
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nRollback interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during rollback: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
