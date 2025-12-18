"""
数据库连接检查脚本
检查PostgreSQL数据库连接状态和Docker容器状态
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse
import subprocess
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_docker_container(container_name: str) -> dict:
    """检查Docker容器状态"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Docker命令执行失败: {result.stderr}",
                "container_exists": False
            }
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        
        if not containers:
            return {
                "status": "not_found",
                "message": f"容器 {container_name} 不存在",
                "container_exists": False
            }
        
        container = containers[0]
        state = container.get("State", "unknown")
        
        return {
            "status": "running" if state == "running" else state,
            "message": f"容器状态: {state}",
            "container_exists": True,
            "container_state": state,
            "container_id": container.get("ID", ""),
            "container_name": container.get("Names", "")
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Docker未安装或不在PATH中",
            "container_exists": False
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"检查容器时出错: {str(e)}",
            "container_exists": False
        }

def check_database_connection(database_url: str) -> dict:
    """检查数据库连接"""
    try:
        parsed = urlparse(database_url)
        
        connection_info = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path[1:] if parsed.path else None,
            "user": parsed.username,
            "password": "***" if parsed.password else None
        }
        
        # 尝试连接
        conn = psycopg2.connect(
            host=connection_info["host"],
            port=connection_info["port"],
            database=connection_info["database"],
            user=connection_info["user"],
            password=parsed.password,
            connect_timeout=5
        )
        
        # 执行测试查询
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog');")
        table_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "status": "connected",
            "message": "数据库连接成功",
            "connection_info": connection_info,
            "database_version": version,
            "current_database": current_db,
            "table_count": table_count
        }
    except psycopg2.OperationalError as e:
        return {
            "status": "connection_failed",
            "message": f"数据库连接失败: {str(e)}",
            "connection_info": connection_info,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"检查数据库时出错: {str(e)}",
            "error": str(e)
        }

def main():
    """主函数"""
    print("=" * 60)
    print("数据库连接检查工具")
    print("=" * 60)
    print()
    
    # 1. 检查Docker容器
    print("1. 检查PostgreSQL Docker容器状态...")
    container_status = check_docker_container("dataagent-postgres")
    print(f"   容器状态: {container_status['status']}")
    print(f"   消息: {container_status['message']}")
    if container_status.get('container_state'):
        print(f"   容器状态详情: {container_status['container_state']}")
    print()
    
    # 2. 检查数据库连接
    print("2. 检查数据库连接...")
    
    # 从环境变量或docker-compose配置获取数据库URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # 尝试从.env文件读取
        env_file = project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        database_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        
        # 如果还是没有，使用默认值
        if not database_url:
            database_url = "postgresql://postgres:password@localhost:5432/dataagent"
            print(f"   警告: 未找到DATABASE_URL环境变量，使用默认值: {database_url.split('@')[1]}")
    
    db_status = check_database_connection(database_url)
    print(f"   连接状态: {db_status['status']}")
    print(f"   消息: {db_status['message']}")
    
    if db_status['status'] == 'connected':
        print(f"   数据库版本: {db_status.get('database_version', 'N/A')[:50]}...")
        print(f"   当前数据库: {db_status.get('current_database', 'N/A')}")
        print(f"   表数量: {db_status.get('table_count', 0)}")
    elif 'connection_info' in db_status:
        conn_info = db_status['connection_info']
        print(f"   连接信息:")
        print(f"     - 主机: {conn_info.get('host', 'N/A')}")
        print(f"     - 端口: {conn_info.get('port', 'N/A')}")
        print(f"     - 数据库: {conn_info.get('database', 'N/A')}")
        print(f"     - 用户: {conn_info.get('user', 'N/A')}")
    print()
    
    # 3. 总结
    print("=" * 60)
    print("检查结果总结")
    print("=" * 60)
    
    all_ok = (
        container_status['status'] == 'running' and 
        db_status['status'] == 'connected'
    )
    
    if all_ok:
        print("✅ 数据库连接正常")
    else:
        print("❌ 数据库连接异常")
        print()
        print("建议检查:")
        if container_status['status'] != 'running':
            print(f"  - Docker容器未运行，请执行: docker start dataagent-postgres")
            print(f"  - 或检查容器状态: docker ps -a | grep dataagent-postgres")
        if db_status['status'] != 'connected':
            print(f"  - 数据库连接失败: {db_status.get('error', '未知错误')}")
            print(f"  - 检查数据库URL是否正确")
            print(f"  - 检查网络连接（如果在Docker中，检查网络配置）")
    
    print()
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

