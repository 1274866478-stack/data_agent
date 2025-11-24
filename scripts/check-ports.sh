#!/bin/bash
# 端口冲突检测脚本 (Linux/macOS)
# 检查Data Agent V4所需的端口是否被占用

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 需要检查的端口
PORTS=(
    "3000:Frontend (Next.js)"
    "8004:Backend (FastAPI)"
    "5432:PostgreSQL"
    "9000:MinIO API"
    "9001:MinIO Console"
    "8001:ChromaDB"
)

echo "=========================================="
echo "Data Agent V4 - 端口冲突检测"
echo "=========================================="
echo ""

CONFLICTS=0

for PORT_INFO in "${PORTS[@]}"; do
    PORT="${PORT_INFO%%:*}"
    SERVICE="${PORT_INFO#*:}"
    
    # 检查端口是否被占用
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${RED}✗${NC} 端口 ${YELLOW}$PORT${NC} 已被占用 - $SERVICE"
        
        # 显示占用端口的进程信息
        PROCESS=$(lsof -Pi :$PORT -sTCP:LISTEN -t | head -1)
        if [ ! -z "$PROCESS" ]; then
            PROCESS_NAME=$(ps -p $PROCESS -o comm= 2>/dev/null || echo "Unknown")
            echo "  占用进程: PID $PROCESS ($PROCESS_NAME)"
        fi
        
        CONFLICTS=$((CONFLICTS + 1))
    else
        echo -e "${GREEN}✓${NC} 端口 ${YELLOW}$PORT${NC} 可用 - $SERVICE"
    fi
done

echo ""
echo "=========================================="

if [ $CONFLICTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有端口可用，可以启动Docker环境${NC}"
    echo ""
    echo "运行以下命令启动服务:"
    echo "  docker-compose up -d"
    exit 0
else
    echo -e "${RED}✗ 发现 $CONFLICTS 个端口冲突${NC}"
    echo ""
    echo "解决方案:"
    echo "1. 停止占用端口的进程"
    echo "2. 修改 docker-compose.yml 中的端口映射"
    echo "3. 使用 docker-compose.override.yml 自定义端口"
    echo ""
    echo "示例 - 停止占用端口的进程:"
    echo "  kill <PID>"
    echo ""
    echo "示例 - 创建 docker-compose.override.yml:"
    echo "  services:"
    echo "    frontend:"
    echo "      ports:"
    echo "        - \"3001:3000\"  # 使用3001代替3000"
    exit 1
fi

