#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 .env 文件编码问题
尝试用不同编码读取文件，然后转换为 UTF-8
"""
import os
from pathlib import Path

def fix_env_encoding(env_file_path):
    """修复 .env 文件编码"""
    env_file = Path(env_file_path)
    
    if not env_file.exists():
        print(f"文件不存在: {env_file_path}")
        return False
    
    # 尝试的编码列表（按优先级）
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
    
    content = None
    used_encoding = None
    
    # 尝试用不同编码读取
    for encoding in encodings:
        try:
            with open(env_file, 'r', encoding=encoding, errors='strict') as f:
                content = f.read()
            used_encoding = encoding
            print(f"成功使用 {encoding} 编码读取文件")
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"使用 {encoding} 编码时出错: {e}")
            continue
    
    if content is None:
        print("无法用任何编码读取文件")
        return False
    
    # 如果已经是 UTF-8，检查是否有问题
    if used_encoding == 'utf-8':
        try:
            # 尝试重新编码验证
            content.encode('utf-8')
            print("文件已经是有效的 UTF-8 编码")
            return True
        except UnicodeEncodeError:
            print("文件标记为 UTF-8 但包含无效字符，尝试修复...")
    
    # 备份原文件
    backup_path = env_file.with_suffix('.env.backup')
    try:
        import shutil
        shutil.copy2(env_file, backup_path)
        print(f"已创建备份: {backup_path}")
    except Exception as e:
        print(f"创建备份失败: {e}")
        return False
    
    # 用 UTF-8 保存
    try:
        with open(env_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"已成功将文件转换为 UTF-8 编码")
        return True
    except Exception as e:
        print(f"保存文件失败: {e}")
        # 恢复备份
        try:
            shutil.copy2(backup_path, env_file)
            print("已恢复备份")
        except:
            pass
        return False

if __name__ == '__main__':
    import sys
    
    # 默认检查 backend/.env
    env_files = [
        Path(__file__).parent.parent / 'backend' / '.env',
        Path(__file__).parent.parent / '.env',
    ]
    
    for env_file in env_files:
        if env_file.exists():
            print(f"\n处理文件: {env_file}")
            if fix_env_encoding(env_file):
                print(f"✓ {env_file} 编码修复成功")
            else:
                print(f"✗ {env_file} 编码修复失败")
                sys.exit(1)
            break
    else:
        print("未找到 .env 文件")
        sys.exit(1)

