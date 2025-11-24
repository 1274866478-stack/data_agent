#!/usr/bin/env python3
"""
日志使用检查工具
检查代码中是否正确使用日志系统
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

# ANSI颜色代码
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def check_file(filepath: Path) -> Dict[str, List[Tuple[int, str]]]:
    """
    检查单个文件的日志使用情况
    
    Returns:
        包含问题的字典: {问题类型: [(行号, 代码行)]}
    """
    issues = {
        'print_statements': [],
        'direct_logging': [],
        'missing_extra': [],
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过注释和空行
            if not stripped or stripped.startswith('#'):
                continue
            
            # 检查print语句 (排除文档字符串和示例代码)
            if re.search(r'\bprint\s*\(', line) and not re.search(r'""".*print.*"""', line):
                # 排除特定的合法使用场景
                if 'print_keys' not in line and 'print_header' not in line:
                    issues['print_statements'].append((i, stripped))
            
            # 检查直接使用logging (应该使用get_logger)
            if re.search(r'import\s+logging', line) and 'from src.app.core.logging import' not in line:
                # 检查是否在logging.py文件中
                if 'logging.py' not in str(filepath):
                    issues['direct_logging'].append((i, stripped))
            
            # 检查logger.info/error等是否缺少extra参数 (简单检查)
            if re.search(r'logger\.(info|warning|error|critical)\s*\([^)]*\)', line):
                if 'extra=' not in line and 'exc_info=' not in line:
                    # 这是一个简化的检查,可能有误报
                    # issues['missing_extra'].append((i, stripped))
                    pass  # 暂时禁用,因为不是所有日志都需要extra
    
    except Exception as e:
        print(f"{Colors.RED}读取文件失败 {filepath}: {e}{Colors.NC}")
    
    return issues


def scan_directory(directory: Path, extensions: List[str] = ['.py']) -> Dict[str, Dict]:
    """
    扫描目录中的所有文件
    
    Returns:
        {文件路径: 问题字典}
    """
    results = {}
    
    for ext in extensions:
        for filepath in directory.rglob(f'*{ext}'):
            # 跳过虚拟环境和缓存目录
            if any(part in filepath.parts for part in ['venv', '__pycache__', '.git', 'node_modules']):
                continue
            
            issues = check_file(filepath)
            
            # 只记录有问题的文件
            if any(issues.values()):
                results[str(filepath)] = issues
    
    return results


def print_results(results: Dict[str, Dict]):
    """打印检查结果"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}日志使用检查报告{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")
    
    total_issues = 0
    
    for filepath, issues in results.items():
        file_has_issues = False
        
        # 打印文件名
        if any(issues.values()):
            print(f"\n{Colors.YELLOW}📄 {filepath}{Colors.NC}")
            file_has_issues = True
        
        # 打印print语句
        if issues['print_statements']:
            print(f"\n  {Colors.RED}❌ 使用print()语句 (应使用logger):{Colors.NC}")
            for line_num, line in issues['print_statements']:
                print(f"     行 {line_num}: {line[:80]}")
                total_issues += 1
        
        # 打印直接使用logging
        if issues['direct_logging']:
            print(f"\n  {Colors.RED}❌ 直接导入logging (应使用get_logger):{Colors.NC}")
            for line_num, line in issues['direct_logging']:
                print(f"     行 {line_num}: {line[:80]}")
                total_issues += 1
        
        # 打印缺少extra参数
        if issues['missing_extra']:
            print(f"\n  {Colors.YELLOW}⚠️  可能缺少extra参数:{Colors.NC}")
            for line_num, line in issues['missing_extra']:
                print(f"     行 {line_num}: {line[:80]}")
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    
    if total_issues == 0:
        print(f"{Colors.GREEN}✅ 未发现日志使用问题!{Colors.NC}")
    else:
        print(f"{Colors.RED}发现 {total_issues} 个日志使用问题{Colors.NC}")
        print(f"\n{Colors.YELLOW}建议:{Colors.NC}")
        print("1. 将print()替换为logger.info()或logger.debug()")
        print("2. 使用 'from src.app.core.logging import get_logger' 获取logger")
        print("3. 在重要日志中添加extra参数提供上下文信息")
        print(f"\n参考文档: backend/docs/Logging-Guide.md")
    
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")
    
    return total_issues


def main():
    """主函数"""
    # 检查后端代码
    backend_dir = Path('backend/src')
    
    if not backend_dir.exists():
        print(f"{Colors.RED}错误: backend/src 目录不存在{Colors.NC}")
        return 1
    
    print(f"{Colors.BLUE}扫描目录: {backend_dir}{Colors.NC}")
    results = scan_directory(backend_dir)
    
    # 打印结果
    total_issues = print_results(results)
    
    return 1 if total_issues > 0 else 0


if __name__ == "__main__":
    exit(main())

