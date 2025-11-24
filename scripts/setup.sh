#!/bin/bash

# Data Agent V4 - 环境初始化脚本
# 用于初始化和配置所有必要的服务和环境

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 命令未找到，请先安装 $1"
        return 1
    fi
    return 0
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        log_warning "端口 $port 已被占用"
        return 1
    fi
    return 0
}

# 等待服务启动
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=$4
    local attempt=1

    log_info "等待 $service_name 服务启动 ($host:$port)..."

    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port &> /dev/null; then
            log_success "$service_name 服务已启动"
            return 0
        fi

        log_info "尝试 $attempt/$max_attempts: $service_name 服务还未就绪，等待 5 秒..."
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "$service_name 服务启动超时"
    return 1
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    # 创建后端目录
    mkdir -p backend/uploads
    mkdir -p backend/logs
    mkdir -p backend/cache

    # 创建日志目录
    mkdir -p logs

    # 创建数据目录
    mkdir -p data/postgres
    mkdir -p data/minio
    mkdir -p data/chroma

    # 创建前端构建目录
    mkdir -p frontend/.next
    mkdir -p frontend/build

    log_success "目录创建完成"
}

# 检查环境变量文件
check_env_files() {
    log_info "检查环境变量文件..."

    # 检查根目录的 .env 文件
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env 文件不存在，正在从 .env.example 创建..."
            cp .env.example .env
            log_warning "请编辑 .env 文件并填入正确的配置值"
        else
            log_error ".env.example 文件不存在"
            return 1
        fi
    fi

    # 检查后端环境变量文件
    if [ ! -f "backend/.env" ]; then
        if [ -f "backend/.env.example" ]; then
            log_warning "backend/.env 文件不存在，正在从 .env.example 创建..."
            cp backend/.env.example backend/.env
            log_warning "请编辑 backend/.env 文件并填入正确的配置值"
        else
            log_error "backend/.env.example 文件不存在"
            return 1
        fi
    fi

    # 检查前端环境变量文件
    if [ ! -f "frontend/.env.local" ]; then
        if [ -f "frontend/.env.local.example" ]; then
            log_warning "frontend/.env.local 文件不存在，正在从 .env.local.example 创建..."
            cp frontend/.env.local.example frontend/.env.local
            log_warning "请编辑 frontend/.env.local 文件并填入正确的配置值"
        else
            log_error "frontend/.env.local.example 文件不存在"
            return 1
        fi
    fi

    log_success "环境变量文件检查完成"
}

# 安装后端依赖
install_backend_dependencies() {
    log_info "安装后端 Python 依赖..."

    if [ -d "backend" ]; then
        cd backend

        # 检查是否有虚拟环境
        if [ ! -d "venv" ]; then
            log_info "创建 Python 虚拟环境..."
            python3 -m venv venv
        fi

        # 激活虚拟环境
        source venv/bin/activate

        # 升级 pip
        pip install --upgrade pip

        # 安装依赖
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        else
            log_error "requirements.txt 文件不存在"
            cd ..
            return 1
        fi

        cd ..
        log_success "后端依赖安装完成"
    else
        log_error "backend 目录不存在"
        return 1
    fi
}

# 安装前端依赖
install_frontend_dependencies() {
    log_info "安装前端 Node.js 依赖..."

    if [ -d "frontend" ]; then
        cd frontend

        # 检查 package.json 是否存在
        if [ -f "package.json" ]; then
            # 安装依赖
            npm install

            log_success "前端依赖安装完成"
        else
            log_error "package.json 文件不存在"
            cd ..
            return 1
        fi

        cd ..
    else
        log_error "frontend 目录不存在"
        return 1
    fi
}

# 启动 Docker 服务
start_docker_services() {
    log_info "启动 Docker 服务..."

    # 检查 docker 命令
    if ! check_command docker; then
        return 1
    fi

    # 检查 docker-compose 命令
    if ! check_command docker-compose; then
        log_error "docker-compose 命令未找到，请先安装 Docker Compose"
        return 1
    fi

    # 检查 Docker 是否正在运行
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请先启动 Docker"
        return 1
    fi

    # 检查端口是否被占用
    check_ports=(3000 5432 8004 9000 9001 8001)
    for port in "${check_ports[@]}"; do
        if ! check_port $port; then
            log_warning "端口 $port 被占用，可能会导致服务启动失败"
        fi
    done

    # 启动服务
    log_info "启动 Docker Compose 服务..."
    docker-compose up -d

    # 等待服务启动
    log_info "等待服务完全启动..."
    sleep 10

    # 等待各个服务启动
    wait_for_service "PostgreSQL" localhost 5432 30
    wait_for_service "MinIO" localhost 9000 30
    wait_for_service "ChromaDB" localhost 8001 30

    log_success "Docker 服务启动完成"
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    # 等待数据库启动
    wait_for_service "PostgreSQL" localhost 5432 30

    # 执行数据库初始化脚本
    if [ -f "backend/scripts/init-db.sql" ]; then
        # 使用 Docker 容器中的 psql 命令执行初始化脚本
        docker exec dataagent-postgres psql -U postgres -d dataagent -f /docker-entrypoint-initdb.d/init-db.sql
        log_success "数据库初始化完成"
    else
        log_warning "数据库初始化脚本不存在，跳过数据库初始化"
    fi
}

# 创建 MinIO 存储桶
create_minio_buckets() {
    log_info "创建 MinIO 存储桶..."

    # 等待 MinIO 启动
    wait_for_service "MinIO" localhost 9000 30

    # 创建存储桶脚本
    cat > /tmp/create_buckets.py << 'EOF'
import sys
from minio import Minio
import os

# MinIO 配置
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"  # 默认值，实际应该从环境变量读取
MINIO_SECRET_KEY = "minioadmin"  # 默认值，实际应该从环境变量读取
BUCKET_NAME = "dataagent-docs"

try:
    # 创建 MinIO 客户端
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    # 检查存储桶是否存在，不存在则创建
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)
        print(f"存储桶 '{BUCKET_NAME}' 创建成功")
    else:
        print(f"存储桶 '{BUCKET_NAME}' 已存在")

except Exception as e:
    print(f"创建存储桶失败: {e}")
    sys.exit(1)
EOF

    # 执行存储桶创建脚本（使用 Python）
    if check_command python3; then
        cd backend
        source venv/bin/activate
        pip install minio
        cd ..
        python3 /tmp/create_buckets.py
        rm -f /tmp/create_buckets.py
        log_success "MinIO 存储桶创建完成"
    else
        log_warning "Python3 未找到，跳过 MinIO 存储桶创建"
    fi
}

# 验证配置
validate_configuration() {
    log_info "验证配置..."

    # 检查必需的环境变量
    required_env_vars=(
        "DATABASE_URL"
        "ZHIPUAI_API_KEY"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
    )

    for var in "${required_env_vars[@]}"; do
        if grep -q "^${var}=" backend/.env; then
            value=$(grep "^${var}=" backend/.env | cut -d'=' -f2-)
            if [[ "$value" == *"your_"* ]] || [[ "$value" == *"example"* ]] || [[ "$value" == *"here"* ]]; then
                log_warning "环境变量 $var 仍使用示例值，请设置真实值"
            fi
        else
            log_error "缺少必需的环境变量: $var"
            return 1
        fi
    done

    log_success "配置验证完成"
}

# 构建前端
build_frontend() {
    log_info "构建前端应用..."

    if [ -d "frontend" ]; then
        cd frontend

        # 安装依赖（如果还没有安装）
        if [ ! -d "node_modules" ]; then
            npm install
        fi

        # 构建应用
        npm run build

        cd ..
        log_success "前端构建完成"
    else
        log_warning "前端目录不存在，跳过构建"
    fi
}

# 显示启动后的信息
show_startup_info() {
    log_success "环境初始化完成！"
    echo
    echo "=== 服务访问信息 ==="
    echo "前端应用: http://localhost:3000"
    echo "后端API: http://localhost:8004"
    echo "API文档: http://localhost:8004/docs"
    echo "MinIO控制台: http://localhost:9001"
    echo "PostgreSQL: localhost:5432"
    echo "ChromaDB: http://localhost:8001"
    echo
    echo "=== 有用的命令 ==="
    echo "查看Docker状态: docker-compose ps"
    echo "查看日志: docker-compose logs -f [service_name]"
    echo "停止服务: docker-compose down"
    echo "重启服务: docker-compose restart [service_name]"
    echo
    echo "=== 验证服务 ==="
    echo "配置验证: curl http://localhost:8004/api/v1/config/validate"
    echo "健康检查: curl http://localhost:8004/api/v1/health"
    echo "测试智谱AI: curl -X POST http://localhost:8004/api/v1/test/zhipu"
    echo
}

# 主函数
main() {
    echo "=== Data Agent V4 环境初始化脚本 ==="
    echo

    # 检查必需的命令
    log_info "检查系统依赖..."
    missing_commands=()

    if ! check_command docker; then
        missing_commands+=("docker")
    fi

    if ! check_command docker-compose; then
        missing_commands+=("docker-compose")
    fi

    if ! check_command npm; then
        missing_commands+=("npm")
    fi

    if ! check_command python3; then
        missing_commands+=("python3")
    fi

    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "缺少以下必需的命令: ${missing_commands[*]}"
        log_error "请先安装这些依赖，然后重新运行脚本"
        exit 1
    fi

    # 执行初始化步骤
    create_directories
    check_env_files
    install_backend_dependencies
    install_frontend_dependencies
    start_docker_services
    init_database
    create_minio_buckets
    validate_configuration
    build_frontend

    show_startup_info

    log_success "所有步骤已完成！"
}

# 处理中断信号
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 运行主函数
main "$@"