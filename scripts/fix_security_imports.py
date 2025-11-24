#!/usr/bin/env python3
"""
修复security.py中的导入和编码问题
"""

import re

file_path = 'backend/src/app/api/v1/endpoints/security.py'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 修复导入
content = content.replace(
    'from ...core.auth import get_current_user',
    'from src.app.core.auth import get_current_user_with_tenant'
)

# 修复所有Depends(get_current_user)为Depends(get_current_user_with_tenant)
content = re.sub(
    r'Depends\(get_current_user\)',
    'Depends(get_current_user_with_tenant)',
    content
)

# 修复其他相对导入
content = re.sub(r'from \.\.\.core\.', 'from src.app.core.', content)
content = re.sub(r'from \.\.\.services\.', 'from src.app.services.', content)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed {file_path}")

