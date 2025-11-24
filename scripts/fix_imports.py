#!/usr/bin/env python3
"""
修复backend中的相对导入为绝对导入
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """修复单个文件中的导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 修复模式: from ...xxx import -> from src.app.xxx import
    # 修复模式: from ....xxx import -> from src.app.xxx import
    
    # 从 api/v1/endpoints/*.py 文件中:
    # from ...core -> from src.app.core
    # from ...services -> from src.app.services
    # from ...data -> from src.app.data
    # from ....data -> from src.app.data
    # from ....services -> from src.app.services
    
    if 'api/v1/endpoints' in str(file_path) or 'api\\v1\\endpoints' in str(file_path):
        # 四个点的导入 (从endpoints到app层)
        content = re.sub(r'from \.\.\.\.(\w+)', r'from src.app.\1', content)
        # 三个点的导入 (从endpoints到api层的兄弟)
        content = re.sub(r'from \.\.\.(\w+)', r'from src.app.\1', content)
    
    # 从 api/v1/*.py 文件中:
    # from ..core -> from src.app.core
    elif 'api/v1' in str(file_path) or 'api\\v1' in str(file_path):
        content = re.sub(r'from \.\.(\w+)', r'from src.app.\1', content)
    
    # 从 core/*.py 文件中:
    # from ..services -> from src.app.services
    # from ..data -> from src.app.data
    elif 'core' in str(file_path):
        content = re.sub(r'from \.\.(\w+)', r'from src.app.\1', content)
        content = re.sub(r'from \.(\w+)', r'from src.app.core.\1', content)
    
    # 从 services/*.py 文件中:
    # from ..core -> from src.app.core
    elif 'services' in str(file_path):
        content = re.sub(r'from \.\.(\w+)', r'from src.app.\1', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed: {file_path}")
        return True
    return False

def main():
    """主函数"""
    backend_path = Path(__file__).parent.parent / 'backend' / 'src' / 'app'
    
    if not backend_path.exists():
        print(f"❌ Backend path not found: {backend_path}")
        return
    
    fixed_count = 0
    for py_file in backend_path.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()

