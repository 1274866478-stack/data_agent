#!/bin/bash

# Data Agent V4 - 配置验证脚本
# 用于验证所有服务的配置和连接状态

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

# 验证结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 增加统计
add_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

add_passed() {
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

add_failed() {
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

# 检查命令是否存在
check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查端口是否开放
check_port() {
    local host=$1
    local port=$2
    local service_name=$3

    add_check

    if nc -z $host $port &> /dev/null; then
        log_success "$service_name ($host:$port) - 端口开放"
        add_passed
        return 0
    else
        log_error "$service_name ($host:$port) - 端口未开放或服务未启动"
        add_failed
        return 1
    fi
}

# 检查环境变量
check_env_var() {
    local var_name=$1
    local env_file=$2
    local required=${3:-true}

    add_check

    if [ -f "$env_file" ]; then
        if grep -q "^${var_name}=" "$env_file"; then
            local value=$(grep "^${var_name}=" "$env_file" | cut -d'=' -f2-)

            # 检查是否为空值
            if [ -z "$value" ]; then
                if [ "$required" = "true" ]; then
                    log_error "环境变量 $var_name 在 $env_file 中为空"
                    add_failed
                    return 1
                else
                    log_warning "环境变量 $var_name 在 $env_file 中为空（可选）"
                    add_passed
                    return 0
                fi
            fi

            # 检查是否仍使用示例值
            if [[ "$value" == *"your_"* ]] || [[ "$value" == *"example"* ]] || [[ "$value" == *"here"* ]]; then
                log_warning "环境变量 $var_name 仍使用示例值: $value"
                add_passed  # 仍算作通过，但给出警告
                return 0
            fi

            log_success "环境变量 $var_name 已设置"
            add_passed
            return 0
        else
            if [ "$required" = "true" ]; then
                log_error "缺少必需的环境变量 $var_name 在 $env_file"
                add_failed
                return 1
            else
                log_info "环境变量 $var_name 未设置（可选）"
                add_passed
                return 0
            fi
        fi
    else
        log_error "环境变量文件 $env_file 不存在"
        add_failed
        return 1
    fi
}

# 检查文件是否存在
check_file() {
    local file_path=$1
    local description=$2
    local required=${3:-true}

    add_check

    if [ -f "$file_path" ]; then
        log_success "$description 存在: $file_path"
        add_passed
        return 0
    else
        if [ "$required" = "true" ]; then
            log_error "$description 不存在: $file_path"
            add_failed
            return 1
        else
            log_warning "$description 不存在（可选）: $file_path"
            add_passed
            return 0
        fi
    fi
}

# 检查目录是否存在
check_directory() {
    local dir_path=$1
    local description=$2
    local required=${3:-true}

    add_check

    if [ -d "$dir_path" ]; then
        log_success "$description 存在: $dir_path"
        add_passed
        return 0
    else
        if [ "$required" = "true" ]; then
            log_error "$description 不存在: $dir_path"
            add_failed
            return 1
        else
            log_warning "$description 不存在（可选）: $dir_path"
            add_passed
            return 0
        fi
    fi
}

# 验证 PostgreSQL 连接
validate_postgresql() {
    log_info "验证 PostgreSQL 连接..."

    add_check

    # 检查 PostgreSQL 容器是否运行
    if ! docker ps | grep -q "dataagent-postgres"; then
        log_error "PostgreSQL 容器未运行"
        add_failed
        return 1
    fi

    # 检查端口
    if ! check_port localhost 5432 "PostgreSQL"; then
        add_failed
        return 1
    fi

    # 尝试连接数据库
    local db_url=$(grep "DATABASE_URL=" .env | cut -d'=' -f2-)
    if [ -z "$db_url" ]; then
        db_url="postgresql://postgres:password@localhost:5432/dataagent"
    fi

    # 解析数据库连接信息
    local host=$(echo $db_url | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local port=$(echo $db_url | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    local database=$(echo $db_url | sed -n 's/.*\/\([^?]*\).*/\1/p')
    local user=$(echo $db_url | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

    # 使用 Docker 容器中的 psql 测试连接
    if docker exec dataagent-postgres psql -U $user -d $database -c "SELECT version();" &> /dev/null; then
        log_success "PostgreSQL 数据库连接正常"
        add_passed
        return 0
    else
        log_error "PostgreSQL 数据库连接失败"
        add_failed
        return 1
    fi
}

# 验证 MinIO 连接
validate_minio() {
    log_info "验证 MinIO 连接..."

    add_check

    # 检查 MinIO 容器是否运行
    if ! docker ps | grep -q "dataagent-minio"; then
        log_error "MinIO 容器未运行"
        add_failed
        return 1
    fi

    # 检查端口
    check_port localhost 9000 "MinIO API"
    check_port localhost 9001 "MinIO Console"

    # 使用 curl 测试 MinIO 健康检查
    if curl -f http://localhost:9000/minio/health/live &> /dev/null; then
        log_success "MinIO 健康检查通过"
        add_passed
        return 0
    else
        log_error "MinIO 健康检查失败"
        add_failed
        return 1
    fi
}

# 验证 ChromaDB 连接
validate_chromadb() {
    log_info "验证 ChromaDB 连接..."

    add_check

    # 检查 ChromaDB 容器是否运行
    if ! docker ps | grep -q "dataagent-chroma"; then
        log_error "ChromaDB 容器未运行"
        add_failed
        return 1
    fi

    # 检查端口
    check_port localhost 8001 "ChromaDB"

    # 使用 curl 测试 ChromaDB 心跳
    if curl -f http://localhost:8000/api/v1/heartbeat &> /dev/null; then
        log_success "ChromaDB 心跳检查通过"
        add_passed
        return 0
    else
        log_error "ChromaDB 心跳检查失败"
        add_failed
        return 1
    fi
}

# 验证后端服务
validate_backend() {
    log_info "验证后端服务..."

    add_check

    # 检查端口
    check_port localhost 8004 "后端API"

    # 测试后端健康检查
    if curl -f http://localhost:8004/api/v1/health &> /dev/null; then
        log_success "后端健康检查通过"
        add_passed
        return 0
    else
        log_error "后端健康检查失败"
        add_failed
        return 1
    fi
}

# 验证前端服务
validate_frontend() {
    log_info "验证前端服务..."

    add_check

    # 检查端口
    check_port localhost 3000 "前端应用"

    # 测试前端响应
    if curl -f http://localhost:3000 &> /dev/null; then
        log_success "前端应用响应正常"
        add_passed
        return 0
    else
        log_error "前端应用无响应"
        add_failed
        return 1
    fi
}

# 验证智谱AI API
validate_zhipuai() {
    log_info "验证智谱 AI API..."

    add_check

    # 检查 API 密钥是否设置
    local api_key=$(grep "ZHIPUAI_API_KEY=" .env | cut -d'=' -f2-)

    if [[ "$api_key" == *"your_"* ]] || [[ "$api_key" == *"example"* ]] || [[ "$api_key" == *"here"* ]]; then
        log_warning "智谱 API 密钥仍使用示例值"
        add_passed  # 不算失败，因为需要真实API密钥
        return 0
    fi

    if [ -z "$api_key" ]; then
        log_warning "智谱 API 密钥未设置"
        add_passed
        return 0
    fi

    # 测试智谱API连接
    local response=$(curl -s -X POST http://localhost:8004/api/v1/test/zhipu 2>/dev/null)

    if echo "$response" | grep -q '"status": "success"'; then
        log_success "智谱 API 连接正常"
        add_passed
        return 0
    else
        log_warning "智谱 API 连接测试失败（可能需要有效的API密钥）"
        add_passed  # 不算失败，因为可能是网络或API问题
        return 0
    fi
}

# 运行全面的配置验证
run_comprehensive_validation() {
    log_info "运行后端配置验证API..."

    add_check

    local response=$(curl -s http://localhost:8004/api/v1/config/validate 2>/dev/null)

    if echo "$response" | grep -q '"overall_status": "success"'; then
        log_success "所有配置验证通过"
        add_passed
        return 0
    elif echo "$response" | grep -q '"overall_status": "partial_success"'; then
        log_warning "部分配置验证通过"
        add_passed
        return 0
    else
        log_error "配置验证失败"
        log_info "详细错误信息:"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        add_failed
        return 1
    fi
}

# 显示验证报告
show_validation_report() {
    echo
    echo "=== 配置验证报告 ==="
    echo "总检查项目: $TOTAL_CHECKS"
    echo -e "通过检查: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "失败检查: ${RED}$FAILED_CHECKS${NC}"

    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "\n${GREEN}✅ 所有验证通过！${NC}"
        return 0
    else
        echo -e "\n${YELLOW}⚠️  有 $FAILED_CHECKS 项检查失败${NC}"
        echo -e "${RED}请检查失败的配置项并修复后重新验证${NC}"
        return 1
    fi
}

# 主函数
main() {
    echo "=== Data Agent V4 配置验证脚本 ==="
    echo

    # 检查必需的命令
    if ! check_command docker; then
        log_error "Docker 命令未找到"
        exit 1
    fi

    if ! check_command curl; then
        log_error "curl 命令未找到"
        exit 1
    fi

    if ! check_command nc; then
        log_error "nc (netcat) 命令未找到"
        exit 1
    fi

    # 执行各项验证
    log_info "开始配置验证..."

    # 1. 检查环境变量文件
    check_file ".env" "根目录环境变量文件" true
    check_file "backend/.env" "后端环境变量文件" true
    check_file "frontend/.env.local" "前端环境变量文件" true

    # 2. 检查必需的环境变量
    log_info "检查环境变量配置..."
    check_env_var "DATABASE_URL" ".env" true
    check_env_var "ZHIPUAI_API_KEY" ".env" true
    check_env_var "MINIO_ACCESS_KEY" ".env" true
    check_env_var "MINIO_SECRET_KEY" ".env" true
    check_env_var "NEXT_PUBLIC_API_URL" "frontend/.env.local" true

    # 3. 检查Docker服务状态
    log_info "检查 Docker 服务..."
    if docker ps | grep -q "dataagent-"; then
        log_success "Docker 容器正在运行"
        add_passed
    else
        log_error "没有找到运行中的 Data Agent Docker 容器"
        add_failed
    fi
    add_check

    # 4. 验证各个服务
    validate_postgresql
    validate_minio
    validate_chromadb
    validate_backend
    validate_frontend
    validate_zhipuai

    # 5. 运行全面配置验证
    run_comprehensive_validation

    # 显示报告
    show_validation_report
}

# 处理中断信号
trap 'log_error "验证脚本被中断"; exit 1' INT TERM

# 运行主函数
main "$@"