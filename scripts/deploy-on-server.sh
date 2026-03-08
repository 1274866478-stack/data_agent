#!/bin/bash
# 腾讯云服务器部署脚本
# 此脚本在服务器上运行

set -e

# 配置变量
PROJECT_NAME="bichat"
PROJECT_DIR="/opt/${PROJECT_NAME}"
DATA_DIR="/opt/bichat_data"
NETWORK_NAME="${PROJECT_NAME}-network"
DEPLOY_DIR="/opt/insight-agent-deploy"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 sudo 执行此脚本"
    exit 1
fi

log_info "======================================"
log_info "  BiChat 腾讯云部署脚本"
log_info "======================================"
echo ""

# 步骤 1: 创建目录
log_info "步骤 1/7: 创建项目目录..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/postgres"
mkdir -p "$DATA_DIR/minio"
mkdir -p "$DATA_DIR/qdrant"
mkdir -p "$DATA_DIR/uploads"
log_info "✓ 目录创建完成"

# 步骤 2: 移动文件
log_info "步骤 2/7: 部署项目文件..."
if [ -d "$DEPLOY_DIR" ]; then
    cp -rn "$DEPLOY_DIR/"* "$PROJECT_DIR/"
    log_info "✓ 文件部署完成"
else
    log_warn "部署目录不存在: $DEPLOY_DIR"
    log_info "假设文件已在 $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 步骤 3: 创建 Docker 网络
log_info "步骤 3/7: 创建独立 Docker 网络..."
if docker network ls | grep -q "$NETWORK_NAME"; then
    log_info "✓ 网络 $NETWORK_NAME 已存在"
else
    docker network create "$NETWORK_NAME"
    log_info "✓ 网络 $NETWORK_NAME 创建成功"
fi

# 步骤 4: 配置环境变量
log_info "步骤 4/7: 配置环境变量..."
if [ ! -f "$PROJECT_DIR/.env.tencent" ]; then
    if [ -f "$PROJECT_DIR/.env.tencent" ]; then
        cp "$PROJECT_DIR/.env.tencent" "$PROJECT_DIR/.env.production"
        log_info "✓ 从 .env.tencent 复制配置"
    else
        log_info "创建 .env.production..."
        cat > "$PROJECT_DIR/.env.production" << 'EOF'
# BiChat 生产环境配置
# 生成时间: $(date)

# PostgreSQL
POSTGRES_PASSWORD=bichat_postgres_secure_password_2026

# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=bichat_minio_secure_password_2026

# DeepSeek API
DEEPSEEK_API_KEY=sk-92bdf5676dc24c50bc8f9868453be410
DEEPSEEK_BASE_URL=https://api.deepseek.com

# JWT Secret
SECRET_KEY=bichat_jwt_secret_key_2026_change_in_production

# 环境
ENVIRONMENT=production
DEBUG=false
EOF
        log_info "✓ .env.production 创建完成"
    fi
else
    log_info "✓ .env.production 已存在"
fi

# 步骤 5: 配置前端环境变量
log_info "步骤 5/7: 配置前端环境变量..."
if [ -f "$PROJECT_DIR/frontend/.env.tencent" ]; then
    cp "$PROJECT_DIR/frontend/.env.tencent" "$PROJECT_DIR/frontend/.env.production"
    log_info "✓ 从 .env.tencent 复制前端配置"
else
    cat > "$PROJECT_DIR/frontend/.env.production" << 'EOF'
# BiChat 前端生产环境配置
NEXT_PUBLIC_API_URL=https://bichat.matrix-ai.com.cn/api/v1
NEXT_PUBLIC_MINIO_ENDPOINT=https://bichat.matrix-ai.com.cn/minio
NEXT_PUBLIC_MINIO_BUCKET=bichat-files
NODE_ENV=production
EOF
fi
log_info "✓ 前端环境配置完成"

# 步骤 6: 停止旧容器
log_info "步骤 6/7: 停止旧容器..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.tencent.yml down 2>/dev/null || true
log_info "✓ 旧容器已停止"

# 步骤 7: 启动服务
log_info "步骤 7/7: 启动 Docker 服务..."
docker compose -f docker-compose.tencent.yml up -d --build

# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 检查容器状态
echo ""
log_info "======================================"
log_info "  容器状态"
log_info "======================================"
docker ps --filter "name=bichat-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
log_info "======================================"
log_info "  部署完成!"
log_info "======================================"
echo ""
log_info "项目目录: $PROJECT_DIR"
log_info "数据目录: $DATA_DIR"
log_info "网络名称: $NETWORK_NAME"
echo ""
log_info "下一步操作:"
echo "  1. 配置 Nginx 反向代理"
echo "  2. 获取 SSL 证书: certbot --nginx -d bichat.matrix-ai.com.cn"
echo ""
log_info "查看日志:"
echo "  docker logs bichat-frontend -f"
echo "  docker logs bichat-backend -f"
echo ""
