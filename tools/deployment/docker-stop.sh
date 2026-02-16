#!/bin/bash
# =============================================================================
# Data Agent V4 - Docker停止脚本
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo -e "${BOLD}${CYAN}"
    echo "==============================================================================="
    echo " Data Agent V4 - Docker环境停止脚本"
    echo " Docker Environment Stop Script"
    echo "==============================================================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 检查Docker Compose命令
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        DOCKER_COMPOSE_CMD="docker compose"
    fi
}

# 停止服务
stop_services() {
    print_info "停止Docker服务..."

    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE_CMD down

    if [ $? -eq 0 ]; then
        print_success "Docker服务已停止"
    else
        print_warning "停止服务时出现警告（可能服务未运行）"
    fi
}

# 清理资源（可选）
cleanup_resources() {
    if [ "$1" = "--cleanup" ]; then
        print_info "清理Docker资源..."

        cd "$PROJECT_ROOT"

        # 停止并删除容器、网络、卷
        $DOCKER_COMPOSE_CMD down -v --remove-orphans

        # 删除悬挂的镜像
        docker image prune -f

        print_success "Docker资源清理完成"
    fi
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --cleanup    停止服务并清理所有相关资源（包括数据卷）"
    echo "  --help, -h   显示此帮助信息"
    echo ""
    echo "注意: 使用--cleanup会删除所有数据，请谨慎使用！"
}

# 主函数
main() {
    print_header

    # 解析命令行参数
    CLEANUP=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 检查Docker Compose
    check_docker_compose

    # 停止服务
    stop_services

    # 清理资源（如果指定）
    if [ "$CLEANUP" = true ]; then
        print_warning "警告: 这将删除所有数据卷，包括数据库数据！"
        read -p "确定要继续吗？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup_resources --cleanup
        else
            print_info "已取消清理操作"
        fi
    fi

    print_success "Data Agent V4 Docker环境已停止"
}

# 运行主函数
main "$@"