#!/usr/bin/env python3
"""
清理旧目录脚本 - 删除重构后残留的旧目录

注意：运行此脚本前请确保：
1. 已停止所有运行的服务
2. 没有程序正在使用这些目录
3. 已验证新目录的文件完整
"""

import shutil
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent.parent

# 需要删除的旧目录
OLD_DIRECTORIES = [
    "frontend",
    "backend",
    "Agent",
    "AgentV2",
    "scripts",  # 如果 tools 目录已完整
]

def cleanup_old_directories():
    """删除旧目录"""

    print("Cleaning up old directories...")
    print("Please ensure all services are stopped before proceeding.")
    print()

    for dir_name in OLD_DIRECTORIES:
        dir_path = ROOT / dir_name

        if not dir_path.exists():
            print(f"  [SKIP] {dir_name} - not found")
            continue

        # 检查是否为符号链接
        if dir_path.is_symlink():
            print(f"  [SKIP] {dir_name} - is a symlink")
            continue

        # 确认删除
        response = input(f"Remove {dir_name}? (yes/no): ")
        if response.lower() != 'yes':
            print(f"  [SKIP] {dir_name} - skipped")
            continue

        try:
            shutil.rmtree(dir_path)
            print(f"  [DONE] {dir_name} - removed")
        except PermissionError:
            print(f"  [ERROR] {dir_name} - permission denied (files in use?)")
        except Exception as e:
            print(f"  [ERROR] {dir_name} - {e}")

    print("\nCleanup complete!")

if __name__ == "__main__":
    cleanup_old_directories()
