#!/usr/bin/env python3
"""
归档项目中的无用文件
将测试文件、调试日志、临时文件等移动到 _archived 文件夹
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 归档目录
ARCHIVE_DIR = ROOT_DIR / "_archived"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARCHIVE_SUBDIR = ARCHIVE_DIR / f"archive_{TIMESTAMP}"

# 需要归档的文件和目录（相对于项目根目录）
FILES_TO_ARCHIVE = [
    # === 调试和日志文件 ===
    "debug",
    "logs",
    "backend/logs",
    "nul",
    
    # === 测试文件（后端根目录） ===
    "backend/test_core_security.py",
    "backend/test_database_adapters.py",
    "backend/test_enhanced_monitoring.py",
    "backend/test_reasoning_basic.py",
    "backend/test_redis_cache.py",
    "backend/test_security_fixes.py",
    "backend/test_story_implementation.py",
    "backend/test_xai_fusion_runner.py",
    "backend/test_zhipu_ai_integration.py",
    "backend/run_v3_integration_tests.py",
    "backend/run_v3_tests_simple.py",
    "backend/security_test_simple.py",
    "backend/simple_test.py",
    "backend/simple_test_runner.py",
    "backend/simple_validation.py",
    "backend/validate_rag_sql_implementation.py",
    
    # === 临时数据库和上传文件 ===
    "backend/test.db",
    "backend/uploads",
    "backend/data/key_rotation.json",
    
    # === 前端构建产物和缓存 ===
    "frontend/coverage",
    "frontend/tsconfig.tsbuildinfo",
    
    # === 文档和报告（可选） ===
    "docs/QA",
    "docs/test-reports",
    "docs/bugfix",
    "apply-qa-fixes.md",
    
    # === 测试工具 ===
    "test-api.html",
]

# 需要保留的关键文件和目录（不归档）
KEEP_FILES = [
    "backend/venv",  # 虚拟环境（太大，用户可自行删除）
    "frontend/node_modules",  # Node依赖（太大，用户可自行删除）
    "backend/tests",  # 测试套件（可能需要）
    "frontend/e2e",  # E2E测试（可能需要）
]


def create_archive_dir():
    """创建归档目录"""
    ARCHIVE_SUBDIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ 创建归档目录: {ARCHIVE_SUBDIR}")


def move_file_or_dir(src_path: Path, dest_base: Path):
    """移动文件或目录到归档位置"""
    if not src_path.exists():
        print(f"⏭️  跳过（不存在）: {src_path}")
        return False
    
    # 计算目标路径（保持相对路径结构）
    rel_path = src_path.relative_to(ROOT_DIR)
    dest_path = dest_base / rel_path
    
    # 创建目标父目录
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        shutil.move(str(src_path), str(dest_path))
        if src_path.is_dir():
            print(f"📁 已移动目录: {rel_path}")
        else:
            print(f"📄 已移动文件: {rel_path}")
        return True
    except Exception as e:
        print(f"❌ 移动失败 {rel_path}: {e}")
        return False


def create_readme():
    """在归档目录创建README说明文件"""
    readme_path = ARCHIVE_SUBDIR / "README.md"
    content = f"""# 归档文件说明

**归档时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 归档内容

本目录包含从 Data Agent V4 项目中归档的无用文件，这些文件不影响项目的正常运行。

### 归档的文件类型

1. **调试和日志文件**: debug/, logs/, backend/logs/
2. **测试文件**: backend/test_*.py, backend/run_v3_*.py
3. **临时数据**: backend/test.db, backend/uploads/
4. **构建产物**: frontend/coverage/, frontend/tsconfig.tsbuildinfo
5. **文档和报告**: docs/QA/, docs/test-reports/, docs/bugfix/

### 如何恢复

如果需要恢复某个文件，可以从本目录复制回项目根目录：

```bash
# 恢复单个文件
cp _archived/archive_{TIMESTAMP}/path/to/file /path/to/original/location

# 恢复整个目录
cp -r _archived/archive_{TIMESTAMP}/path/to/dir /path/to/original/location
```

### 安全删除

确认不再需要这些文件后，可以安全删除整个归档目录：

```bash
rm -rf _archived/archive_{TIMESTAMP}
```

## 注意事项

- ✅ 项目核心代码未被移动
- ✅ 配置文件保持不变
- ✅ Docker配置未受影响
- ✅ 依赖管理文件完整

如有疑问，请参考项目文档: CLAUDE.md
"""
    
    readme_path.write_text(content, encoding="utf-8")
    print(f"📝 已创建说明文件: README.md")


def main():
    print("=" * 60)
    print("Data Agent V4 - 归档无用文件")
    print("=" * 60)
    print()
    
    # 创建归档目录
    create_archive_dir()
    print()
    
    # 统计
    moved_count = 0
    skipped_count = 0
    
    # 移动文件
    print("开始归档文件...")
    print()
    for file_path_str in FILES_TO_ARCHIVE:
        src_path = ROOT_DIR / file_path_str
        if move_file_or_dir(src_path, ARCHIVE_SUBDIR):
            moved_count += 1
        else:
            skipped_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ 归档完成！")
    print(f"   - 已移动: {moved_count} 项")
    print(f"   - 已跳过: {skipped_count} 项")
    print(f"   - 归档位置: {ARCHIVE_SUBDIR}")
    print("=" * 60)
    
    # 创建README
    create_readme()
    
    print()
    print("💡 提示:")
    print("   1. 虚拟环境和node_modules未被移动（太大），可手动删除")
    print("   2. 测试套件(backend/tests, frontend/e2e)已保留")
    print("   3. 如需恢复文件，请查看归档目录中的README.md")
    print()


if __name__ == "__main__":
    main()

