#!/usr/bin/env python3
"""
完全修复security.py的编码问题
"""

import re

file_path = 'backend/src/app/api/v1/endpoints/security.py'

# 读取文件，忽略编码错误
with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# 修复每一行的编码问题
fixed_lines = []
for i, line in enumerate(lines, 1):
    # 替换常见的乱码模式
    line = line.replace('杩斿洖璁板綍鏁伴檺锟?', '返回记录数限制')
    line = line.replace('涓瘑閽ュ嵆灏嗚繃锟?', '个密钥即将过期')
    line = line.replace('锟?', '"')
    line = line.replace('�', '')
    
    # 确保所有字符串都正确闭合
    # 如果行包含description=但没有正确闭合，修复它
    if 'description=' in line and line.count('"') % 2 != 0:
        # 在行尾添加缺失的引号
        line = line.rstrip() + '"\n' if not line.rstrip().endswith('"') else line
    
    fixed_lines.append(line)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print(f"✅ Fixed encoding in {file_path}")
print(f"   Total lines: {len(fixed_lines)}")

