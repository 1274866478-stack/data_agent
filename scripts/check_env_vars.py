#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查环境变量配置脚本
验证 Agent 集成所需的环境变量是否已设置
"""
import os
import sys
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 尝试加载 .env 文件（如果存在）
env_files = [
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent / "backend" / ".env",
    Path(__file__).parent.parent / "Agent" / ".env"
]

for env_file in env_files:
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"已加载环境变量文件: {env_file}")
        except Exception as e:
            print(f"警告: 无法加载 {env_file}: {e}")

print("\n" + "="*60)
print("环境变量检查")
print("="*60)

# 必需的环境变量
required_vars = {
    "DEEPSEEK_API_KEY": "DeepSeek API 密钥（必需）",
    "DATABASE_URL": "数据库连接字符串（必需）"
}

# 可选的环境变量
optional_vars = {
    "DEEPSEEK_BASE_URL": "DeepSeek API 基础 URL（可选，默认: https://api.deepseek.com）",
    "DEEPSEEK_MODEL": "DeepSeek 模型名称（可选，默认: deepseek-chat）"
}

print("\n必需的环境变量:")
all_required_set = True
for var, desc in required_vars.items():
    value = os.getenv(var)
    if value:
        # 只显示前10个字符，隐藏完整密钥
        display_value = value[:10] + "..." if len(value) > 10 else value
        print(f"  [OK] {var}: {display_value} ({desc})")
    else:
        print(f"  [X] {var}: 未设置 ({desc})")
        all_required_set = False

print("\n可选的环境变量:")
for var, desc in optional_vars.items():
    value = os.getenv(var)
    if value:
        print(f"  [OK] {var}: {value} ({desc})")
    else:
        default = desc.split("默认: ")[1].split("）")[0] if "默认: " in desc else "未设置"
        print(f"  [-] {var}: 未设置，将使用默认值 ({desc})")

print("\n" + "="*60)
if all_required_set:
    print("[SUCCESS] 所有必需的环境变量已设置！")
    print("="*60)
    sys.exit(0)
else:
    print("[WARNING] 部分必需的环境变量未设置")
    print("\n请设置以下环境变量:")
    for var, desc in required_vars.items():
        if not os.getenv(var):
            print(f"  - {var}: {desc}")
    print("\n设置方法:")
    print("  1. 在项目根目录创建 .env 文件")
    print("  2. 添加环境变量，例如:")
    print("     DEEPSEEK_API_KEY=your_api_key_here")
    print("     DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
    print("="*60)
    sys.exit(1)
