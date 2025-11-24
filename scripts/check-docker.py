#!/usr/bin/env python3
"""
Data Agent V4 - Docker配置检查工具
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    print("=" * 70)
    print("Data Agent V4 - Docker配置检查工具")
    print("=" * 70)

def check_file_exists(filepath, description):
    if Path(filepath).exists():
        print(f"[OK] {description}: {filepath}")
        return True
    else:
        print(f"[ERROR] {description}不存在: {filepath}")
        return False

def check_docker_files():
    print("\n检查Docker相关文件...")

    required_files = [
        ("docker-compose.yml", "Docker Compose配置"),
        (".env.example", "环境变量模板"),
        ("frontend/Dockerfile", "前端Dockerfile"),
        ("backend/Dockerfile", "后端Dockerfile"),
        ("backend/requirements.txt", "后端依赖"),
        ("frontend/package.json", "前端依赖"),
        ("backend/scripts/init-db.sql", "数据库初始化脚本")
    ]

    all_ok = True
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_ok = False

    return all_ok

def check_directories():
    print("\n检查目录结构...")

    required_dirs = ["frontend", "backend", "scripts", "docs"]
    all_ok = True

    for dir_name in required_dirs:
        if Path(dir_name).exists() and Path(dir_name).is_dir():
            print(f"[OK] 目录存在: {dir_name}/")
        else:
            print(f"[ERROR] 目录缺失: {dir_name}/")
            all_ok = False

    return all_ok

def check_env_file():
    print("\n检查环境变量配置...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_example.exists():
        print("[ERROR] .env.example文件不存在")
        return False

    print("[OK] .env.example文件存在")

    if not env_file.exists():
        print("[WARNING] .env文件不存在，请复制.env.example并配置")
        return False

    # 检查关键环境变量
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if "your_zhipuai_api_key_here" in content:
            print("[WARNING] 请配置真实的ZHIPUAI_API_KEY")

        if "your-super-secret-key" in content:
            print("[WARNING] 请配置强密码SECRET_KEY")

        print("[OK] 环境变量文件检查完成")
        return True

    except Exception as e:
        print(f"[ERROR] 读取.env文件失败: {e}")
        return False

def check_docker_daemon():
    print("\n检查Docker环境...")

    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"[OK] Docker已安装: {result.stdout.strip()}")
        else:
            print("[ERROR] Docker未正确安装")
            return False

        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("[OK] Docker守护进程运行正常")
            return True
        else:
            print("[ERROR] Docker守护进程未运行")
            return False

    except FileNotFoundError:
        print("[ERROR] Docker未安装或不在PATH中")
        return False
    except subprocess.TimeoutExpired:
        print("[ERROR] Docker命令超时")
        return False
    except Exception as e:
        print(f"[ERROR] 检查Docker时发生错误: {e}")
        return False

def check_docker_compose_syntax():
    print("\n检查Docker Compose语法...")

    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("[ERROR] docker-compose.yml文件不存在")
        return False

    try:
        result = subprocess.run(
            ['docker', 'compose', '-f', str(compose_file), 'config', '--quiet'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] docker-compose.yml语法正确")
            return True
        else:
            print(f"[ERROR] docker-compose.yml语法错误: {result.stderr}")
            return False

    except FileNotFoundError:
        print("[WARNING] Docker Compose未找到，跳过语法检查")
        return True
    except subprocess.TimeoutExpired:
        print("[ERROR] Docker Compose命令超时")
        return False
    except Exception as e:
        print(f"[ERROR] 检查Docker Compose时发生错误: {e}")
        return False

def main():
    print_header()

    checks = [
        ("项目结构", check_directories),
        ("Docker文件", check_docker_files),
        ("环境变量", check_env_file),
        ("Docker环境", check_docker_daemon),
        ("Docker Compose语法", check_docker_compose_syntax)
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"[ERROR] {check_name}检查失败: {e}")
            results.append((check_name, False))

    # 显示总结
    print("\n" + "=" * 70)
    print("检查结果总结:")
    print("=" * 70)

    success_count = 0
    for check_name, result in results:
        status = "[OK]" if result else "[ERROR]"
        print(f"{status} {check_name}")
        if result:
            success_count += 1

    print(f"\n总计: {success_count}/{len(results)} 项检查通过")

    if success_count == len(results):
        print("\n[SUCCESS] 所有检查通过！Docker环境配置正确。")
        print("可以运行以下命令启动环境:")
        print("  docker compose up -d")
        print("  或者使用启动脚本:")
        print("  scripts/docker-start.bat  (Windows)")
        print("  ./scripts/docker-start.sh  (Linux/Mac)")
        return True
    else:
        print(f"\n[ERROR] {len(results) - success_count} 项检查失败，请修复后重试。")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)