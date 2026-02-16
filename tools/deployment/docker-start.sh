#!/bin/bash
# =============================================================================
# Data Agent V4 - Docker启动脚本
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 打印标题
print_header() {
    echo -e "${BOLD}${CYAN}"
    echo "==============================================================================="
    echo " Data Agent V4 - Docker环境启动脚本"
    echo " Docker Environment Startup Script"
    echo "==============================================================================="
    echo -e "${NC}"
}

# 打印带颜色的消息
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查Docker是否安装和运行
check_docker() {
    print_info "检查Docker环境..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker守护进程未运行，请启动Docker"
        exit 1
    fi

    print_success "Docker环境正常"

    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        DOCKER_COMPOSE_CMD="docker compose"
    fi

    print_info "使用命令: $DOCKER_COMPOSE_CMD"
}

# 检查环境变量文件
check_env_file() {
    print_info "检查环境变量配置..."

    ENV_FILE="$PROJECT_ROOT/.env"

    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env文件不存在"

        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            print_info "从.env.example创建.env文件..."
            cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
            print_success "已创建.env文件"
            print_warning "请编辑.env文件并配置真实的API密钥和密码"
        else
            print_error ".env.example文件不存在"
            exit 1
        fi
    fi

    # 检查关键环境变量
    if grep -q "your_zhipuai_api_key_here" "$ENV_FILE"; then
        print_warning "请配置真实的ZHIPUAI_API_KEY"
    fi

    if grep -q "your-super-secret-key" "$ENV_FILE"; then
        print_warning "请配置强密码SECRET_KEY"
    fi

    print_success "环境变量文件检查完成"
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."

    directories=(
        "$PROJECT_ROOT/backend/logs"
        "$PROJECT_ROOT/backend/uploads"
        "$PROJECT_ROOT/backend/temp"
        "$PROJECT_ROOT/frontend/logs"
        "$PROJECT_ROOT/data/postgres"
        "$PROJECT_ROOT/data/minio"
        "$PROJECT_ROOT/data/chroma"
    )

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "创建目录: $dir"
        fi
    done
}

# 构建Docker镜像
build_images() {
    print_info "构建Docker镜像..."

    cd "$PROJECT_ROOT"

    if [ "$1" = "--rebuild" ]; then
        print_info "强制重新构建所有镜像..."
        $DOCKER_COMPOSE_CMD build --no-cache
    else
        $DOCKER_COMPOSE_CMD build
    fi

    if [ $? -eq 0 ]; then
        print_success "Docker镜像构建完成"
    else
        print_error "Docker镜像构建失败"
        exit 1
    fi
}

# 启动服务
start_services() {
    print_info "启动Docker服务..."

    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE_CMD up -d

    if [ $? -eq 0 ]; then
        print_success "Docker服务启动成功"
    else
        print_error "Docker服务启动失败"
        exit 1
    fi
}

# 等待服务就绪
wait_for_services() {
    print_info "等待服务就绪..."

    # 等待数据库启动
    print_info "等待PostgreSQL数据库启动..."
    timeout 60 bash -c 'until docker exec dataagent-postgres pg_isready -U postgres -d dataagent; do sleep 2; done'

    if [ $? -eq 0 ]; then
        print_success "PostgreSQL数据库已就绪"
    else
        print_warning "PostgreSQL数据库启动超时"
    fi

    # 等待后端服务启动
    print_info "等待后端API服务启动..."
    timeout 60 bash -c 'until curl -f http://localhost:8004/health &>/dev/null; do sleep 3; done'

    if [ $? -eq 0 ]; then
        print_success "后端API服务已就绪"
    else
        print_warning "后端API服务启动超时"
    fi

    # 等待前端服务启动
    print_info "等待前端服务启动..."
    timeout 60 bash -c 'until curl -f http://localhost:3000 &>/dev/null; do sleep 3; done'

    if [ $? -eq 0 ]; then
        print_success "前端服务已就绪"
    else
        print_warning "前端服务启动超时"
    fi
}

# 显示服务状态
show_status() {
    print_info "服务状态:"
    echo ""

    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE_CMD ps

    echo ""
    print_info "服务访问地址:"
    echo "  前端应用:    http://localhost:3000"
    echo "  后端API:     http://localhost:8004"
    echo "  API文档:     http://localhost:8004/docs"
    echo "  MinIO控制台: http://localhost:9001"
    echo "  ChromaDB:    http://localhost:8001"
    echo ""
}

# 显示有用的命令
show_commands() {
    print_info "常用命令:"
    echo "  查看日志:     $DOCKER_COMPOSE_CMD logs -f [service_name]"
    echo "  停止服务:     $DOCKER_COMPOSE_CMD down"
    echo "  重启服务:     $DOCKER_COMPOSE_CMD restart [service_name]"
    echo "  进入容器:     docker exec -it dataagent-backend bash"
    echo "  数据库连接:   docker exec -it dataagent-postgres psql -U postgres -d dataagent"
    echo ""
}

# 验证配置
validate_config() {
    print_info "验证配置..."

    if [ -f "$PROJECT_ROOT/scripts/validate-docker-config.py" ]; then
        python "$PROJECT_ROOT/scripts/validate-docker-config.py" --env-file .env
    else
        print_warning "配置验证脚本不存在，跳过验证"
    fi
}

# 主函数
main() {
    print_header

    # 解析命令行参数
    REBUILD=false
    SKIP_BUILD=false
    VALIDATE_ONLY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --rebuild)
                REBUILD=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            --help|-h)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --rebuild        强制重新构建所有镜像"
                echo "  --skip-build     跳过镜像构建"
                echo "  --validate-only  仅验证配置，不启动服务"
                echo "  --help, -h       显示此帮助信息"
                echo ""
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 仅验证配置
    if [ "$VALIDATE_ONLY" = true ]; then
        validate_config
        exit 0
    fi

    # 执行启动流程
    check_docker
    check_env_file
    create_directories

    # 验证配置
    if [ -f "$PROJECT_ROOT/scripts/validate-docker-config.py" ]; then
        validate_config
        echo ""
    fi

    # 构建镜像
    if [ "$SKIP_BUILD" = false ]; then
        if [ "$REBUILD" = true ]; then
            build_images --rebuild
        else
            build_images
        fi
    fi

    # 启动服务
    start_services

    # 等待服务就绪
    wait_for_services

    # 显示状态和命令
    show_status
    show_commands

    print_success "Data Agent V4 Docker环境启动完成！"
    print_info "如果遇到问题，请查看日志: $DOCKER_COMPOSE_CMD logs -f"
}

# 运行主函数
main "$@"