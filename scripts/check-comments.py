#!/usr/bin/env python3
"""
代码注释语言检查工具
检查代码中注释的语言使用情况,统计中英文注释比例
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# ANSI颜色代码
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def has_chinese(text: str) -> bool:
    """检查文本是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def has_english_words(text: str) -> bool:
    """检查文本是否包含英文单词(排除代码关键字)"""
    # 移除代码相关内容
    text = re.sub(r'[{}()\[\];,.<>]', ' ', text)
    text = re.sub(r'\b(def|class|import|from|return|if|else|for|while|try|except|async|await)\b', '', text)
    
    # 检查是否有英文单词
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    return len(words) > 0


def extract_comments_python(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    提取Python文件中的注释
    
    Returns:
        [(行号, 注释内容, 语言类型)]
    """
    comments = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_docstring = False
        docstring_start = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过空行
            if not stripped:
                continue
            
            # 检测文档字符串
            if '"""' in stripped or "'''" in stripped:
                if not in_docstring:
                    in_docstring = True
                    docstring_start = i
                else:
                    in_docstring = False
                    # 文档字符串结束,不单独统计
                continue
            
            # 跳过文档字符串内部
            if in_docstring:
                continue
            
            # 检测单行注释
            if stripped.startswith('#'):
                comment = stripped[1:].strip()
                
                # 跳过特殊注释
                if comment.startswith('!') or comment.startswith('-*-'):
                    continue
                
                # 判断语言
                lang = 'unknown'
                if has_chinese(comment):
                    lang = 'chinese'
                elif has_english_words(comment):
                    lang = 'english'
                
                if lang != 'unknown':
                    comments.append((i, comment, lang))
    
    except Exception as e:
        print(f"{Colors.RED}读取文件失败 {filepath}: {e}{Colors.NC}")
    
    return comments


def extract_comments_typescript(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    提取TypeScript/JavaScript文件中的注释
    
    Returns:
        [(行号, 注释内容, 语言类型)]
    """
    comments = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_block_comment = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过空行
            if not stripped:
                continue
            
            # 检测块注释
            if '/*' in stripped:
                in_block_comment = True
            
            if in_block_comment:
                # 提取块注释内容
                comment = re.sub(r'/\*|\*/|\*', '', stripped).strip()
                
                if comment and not comment.startswith('@'):
                    lang = 'unknown'
                    if has_chinese(comment):
                        lang = 'chinese'
                    elif has_english_words(comment):
                        lang = 'english'
                    
                    if lang != 'unknown':
                        comments.append((i, comment, lang))
                
                if '*/' in stripped:
                    in_block_comment = False
                continue
            
            # 检测单行注释
            if '//' in stripped:
                comment_match = re.search(r'//(.*)', stripped)
                if comment_match:
                    comment = comment_match.group(1).strip()
                    
                    # 跳过特殊注释
                    if comment.startswith('@') or comment.startswith('eslint'):
                        continue
                    
                    lang = 'unknown'
                    if has_chinese(comment):
                        lang = 'chinese'
                    elif has_english_words(comment):
                        lang = 'english'
                    
                    if lang != 'unknown':
                        comments.append((i, comment, lang))
    
    except Exception as e:
        print(f"{Colors.RED}读取文件失败 {filepath}: {e}{Colors.NC}")
    
    return comments


def scan_directory(directory: Path, file_types: Dict[str, callable]) -> Dict[str, List]:
    """
    扫描目录中的所有文件
    
    Returns:
        {文件路径: [(行号, 注释, 语言)]}
    """
    results = {}
    
    for ext, extractor in file_types.items():
        for filepath in directory.rglob(f'*{ext}'):
            # 跳过特定目录
            if any(part in filepath.parts for part in ['venv', '__pycache__', '.git', 'node_modules', 'dist', 'build']):
                continue
            
            comments = extractor(filepath)
            
            if comments:
                results[str(filepath)] = comments
    
    return results


def print_statistics(results: Dict[str, List]):
    """打印统计结果"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}代码注释语言统计报告{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")
    
    total_chinese = 0
    total_english = 0
    mixed_files = []
    
    for filepath, comments in results.items():
        chinese_count = sum(1 for _, _, lang in comments if lang == 'chinese')
        english_count = sum(1 for _, _, lang in comments if lang == 'english')
        
        total_chinese += chinese_count
        total_english += english_count
        
        # 检测混用文件
        if chinese_count > 0 and english_count > 0:
            mixed_files.append((filepath, chinese_count, english_count))
    
    # 打印总体统计
    total = total_chinese + total_english
    if total > 0:
        chinese_percent = (total_chinese / total) * 100
        english_percent = (total_english / total) * 100
        
        print(f"{Colors.CYAN}总体统计:{Colors.NC}")
        print(f"  中文注释: {total_chinese} ({chinese_percent:.1f}%)")
        print(f"  英文注释: {total_english} ({english_percent:.1f}%)")
        print(f"  总计: {total}")
        
        # 判断主要语言
        if chinese_percent > 60:
            print(f"\n{Colors.GREEN}✅ 建议: 项目主要使用中文注释,建议统一使用中文{Colors.NC}")
        elif english_percent > 60:
            print(f"\n{Colors.GREEN}✅ 建议: 项目主要使用英文注释,建议统一使用英文{Colors.NC}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  建议: 中英文注释混用,建议统一使用一种语言{Colors.NC}")
    
    # 打印混用文件
    if mixed_files:
        print(f"\n{Colors.YELLOW}混用文件 ({len(mixed_files)}个):{Colors.NC}")
        for filepath, cn, en in mixed_files[:10]:  # 只显示前10个
            print(f"  {filepath}")
            print(f"    中文: {cn}, 英文: {en}")
        
        if len(mixed_files) > 10:
            print(f"  ... 还有 {len(mixed_files) - 10} 个文件")
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}\n")


def main():
    """主函数"""
    # 检查后端代码
    backend_dir = Path('backend/src')
    frontend_dir = Path('frontend/src')
    
    results = {}
    
    if backend_dir.exists():
        print(f"{Colors.BLUE}扫描后端代码: {backend_dir}{Colors.NC}")
        backend_results = scan_directory(backend_dir, {'.py': extract_comments_python})
        results.update(backend_results)
    
    if frontend_dir.exists():
        print(f"{Colors.BLUE}扫描前端代码: {frontend_dir}{Colors.NC}")
        frontend_results = scan_directory(frontend_dir, {
            '.ts': extract_comments_typescript,
            '.tsx': extract_comments_typescript,
            '.js': extract_comments_typescript,
            '.jsx': extract_comments_typescript,
        })
        results.update(frontend_results)
    
    # 打印统计
    print_statistics(results)


if __name__ == "__main__":
    main()

