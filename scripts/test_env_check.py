"""
环境检查脚本 - 检查测试所需的基本环境
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
backend_src = project_root / "backend" / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_src))

print("=" * 80)
print("环境检查")
print("=" * 80)

# 检查Python版本
print(f"\n1. Python版本: {sys.version}")

# 检查项目路径
print(f"\n2. 项目根目录: {project_root}")
print(f"   Backend源码目录: {backend_src}")
print(f"   目录存在: {backend_src.exists()}")

# 检查关键文件
key_files = [
    "backend/src/app/services/agent/agent_service.py",
    "backend/src/app/services/agent/tools.py",
    "backend/src/app/core/config.py",
]

print("\n3. 关键文件检查:")
for file_path in key_files:
    full_path = project_root / file_path
    exists = full_path.exists()
    status = "[OK]" if exists else "[MISSING]"
    print(f"   {status} {file_path}")

# 尝试导入模块
print("\n4. 模块导入检查:")
try:
    try:
        from src.app.core.config import settings
        print("   [OK] 从 src.app 导入成功")
    except ImportError as e1:
        try:
            from backend.src.app.core.config import settings
            print("   [OK] 从 backend.src.app 导入成功")
        except ImportError as e2:
            print(f"   [FAIL] 导入失败: {e2}")
            raise
except Exception as e:
    print(f"   [FAIL] 导入错误: {e}")

# 检查环境变量
print("\n5. 环境变量检查:")
import os
env_vars = ["DATABASE_URL", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY"]
for var in env_vars:
    value = os.environ.get(var)
    if value:
        # 只显示前20个字符
        preview = value[:20] + "..." if len(value) > 20 else value
        print(f"   [OK] {var}: {preview}")
    else:
        print(f"   [WARN] {var}: 未设置")

print("\n" + "=" * 80)
print("环境检查完成")
print("=" * 80)

