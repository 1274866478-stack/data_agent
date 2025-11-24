#!/usr/bin/env python3
"""
端口冲突检测脚本 (跨平台)
检查Data Agent V4所需的端口是否被占用
"""

import socket
import sys
import platform
from typing import Dict, List, Tuple

# ANSI颜色代码
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'  # No Color
    
    @staticmethod
    def disable_on_windows():
        """在Windows上禁用颜色（除非使用Windows Terminal）"""
        if platform.system() == 'Windows':
            try:
                import colorama
                colorama.init()
            except ImportError:
                # 如果没有colorama，禁用颜色
                Colors.RED = Colors.GREEN = Colors.YELLOW = ''
                Colors.CYAN = Colors.GRAY = Colors.NC = ''


# 需要检查的端口
PORTS: Dict[int, str] = {
    3000: "Frontend (Next.js)",
    8004: "Backend (FastAPI)",
    5432: "PostgreSQL",
    9000: "MinIO API",
    9001: "MinIO Console",
    8001: "ChromaDB",
}


def check_port(port: int) -> bool:
    """
    检查端口是否被占用
    
    Args:
        port: 端口号
        
    Returns:
        True if port is in use, False otherwise
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    
    try:
        # 尝试绑定端口
        sock.bind(('127.0.0.1', port))
        sock.close()
        return False  # 端口可用
    except socket.error:
        return True  # 端口被占用
    finally:
        sock.close()


def get_process_using_port(port: int) -> str:
    """
    获取占用端口的进程信息（仅在支持的平台上）
    
    Args:
        port: 端口号
        
    Returns:
        进程信息字符串
    """
    try:
        import psutil
        
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    return f"PID {conn.pid} ({process.name()})"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return f"PID {conn.pid}"
        return "Unknown"
    except ImportError:
        return "安装 psutil 以查看进程信息: pip install psutil"


def main():
    """主函数"""
    Colors.disable_on_windows()
    
    print(f"{Colors.CYAN}=========================================={Colors.NC}")
    print(f"{Colors.CYAN}Data Agent V4 - 端口冲突检测{Colors.NC}")
    print(f"{Colors.CYAN}=========================================={Colors.NC}")
    print()
    
    conflicts: List[Tuple[int, str]] = []
    
    # 按端口号排序检查
    for port in sorted(PORTS.keys()):
        service = PORTS[port]
        
        if check_port(port):
            print(f"{Colors.RED}✗{Colors.NC} 端口 {Colors.YELLOW}{port}{Colors.NC} 已被占用 - {service}")
            
            # 尝试获取进程信息
            process_info = get_process_using_port(port)
            print(f"{Colors.GRAY}  占用进程: {process_info}{Colors.NC}")
            
            conflicts.append((port, service))
        else:
            print(f"{Colors.GREEN}✓{Colors.NC} 端口 {Colors.YELLOW}{port}{Colors.NC} 可用 - {service}")
    
    print()
    print(f"{Colors.CYAN}=========================================={Colors.NC}")
    
    if not conflicts:
        print(f"{Colors.GREEN}✓ 所有端口可用，可以启动Docker环境{Colors.NC}")
        print()
        print("运行以下命令启动服务:")
        print(f"{Colors.CYAN}  docker-compose up -d{Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}✗ 发现 {len(conflicts)} 个端口冲突{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}解决方案:{Colors.NC}")
        print("1. 停止占用端口的进程")
        print("2. 修改 docker-compose.yml 中的端口映射")
        print("3. 使用 docker-compose.override.yml 自定义端口")
        print()
        print(f"{Colors.YELLOW}示例 - 创建 docker-compose.override.yml:{Colors.NC}")
        print(f"{Colors.CYAN}  services:{Colors.NC}")
        print(f"{Colors.CYAN}    frontend:{Colors.NC}")
        print(f"{Colors.CYAN}      ports:{Colors.NC}")
        print(f"{Colors.CYAN}        - \"3001:3000\"  # 使用3001代替3000{Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

