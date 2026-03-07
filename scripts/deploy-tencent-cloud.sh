#!/bin/bash
# 腾讯云 CVM 一键部署脚本
# 使用方法: sudo bash scripts/deploy-tencent-cloud.sh your-domain.com

set -e  # 遇到错误立即退出

DOMAIN=${1:-"your-domain.com"}
PROJECT_DIR="/opt/dataagent"

echo "========================================"
echo "  Data Agent 腾讯云部署脚本"
echo "  域名: $DOMAIN"
echo "========================================"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 安装基础软件
echo "[1/8] 安装 Docker 和 Nginx..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

if ! command -v nginx &> /dev/null; then
    yum install -y nginx 2>/dev/null || apt install -y nginx
    systemctl enable nginx
fi

# 2. 创建数据目录
echo "[2/8] 创建数据存储目录..."
mkdir -p /opt/bichat_data/{postgres,minio,qdrant,uploads}
chown -R 999:999 /opt/bichat_data/postgres  # PostgreSQL 容器用户
chown -R 1000:1000 /opt/bichat_data/minio   # MinIO 容器用户

# 3. 生成安全密钥
echo "[3/8] 生成安全密钥..."
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24)
MINIO_PASSWORD=$(openssl rand -base64 24)

# 4. 创建生产环境配置
echo "[4/8] 创建生产环境配置..."
cat > $PROJECT_DIR/.env.production << EOF
# ========== 数据库 ==========
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# ========== MinIO ==========
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=$MINIO_PASSWORD
MINIO_ACCESS_KEY=minio_access_$(openssl rand -hex 8)
MINIO_SECRET_KEY=minio_secret_$(openssl rand -hex 16)

# ========== 应用安全 ==========
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# ========== Cube.js ==========
CUBEJS_API_SECRET=cube_secret_$(openssl rand -hex 16)

# ========== 生产环境 ==========
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ========== CORS ==========
CORS_ORIGINS=["https://$DOMAIN","https://www.$DOMAIN"]

# ========== SOTA 特性 ==========
USE_SOTA_AGENT=true
ENABLE_SEMANTIC_LAYER=true
ENABLE_FEW_SHOT_RAG=true
ENABLE_SELF_HEALING=true

# ========== LLM API (请手动添加) ==========
DEEPSEEK_API_KEY=your_deepseek_key_here
ZHIPUAI_API_KEY=your_zhipuai_key_here
EOF

echo "生产环境配置已创建: $PROJECT_DIR/.env.production"
echo "⚠️  请手动编辑此文件，添加你的 LLM API 密钥"

# 5. 配置 Nginx
echo "[5/8] 配置 Nginx..."
sed "s/your-domain.com/$DOMAIN/g" $PROJECT_DIR/nginx.conf > /etc/nginx/conf.d/dataagent.conf
mkdir -p /var/www/html

# 6. 安装 SSL 证书 (Let's Encrypt)
echo "[6/8] 安装 SSL 证书..."
if ! command -v certbot &> /dev/null; then
    yum install -y certbot python3-certbot-nginx 2>/dev/null || apt install -y certbot python3-certbot-nginx
fi

echo "请确保域名 $DOMAIN 已解析到此服务器，然后运行:"
echo "  certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
read -p "SSL 证书已配置? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "跳过证书配置，请稍后手动配置"
fi

# 7. 启动 Docker 服务
echo "[7/8] 启动 Docker 服务..."
cd $PROJECT_DIR
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 8. 配置防火墙
echo "[8/8] 配置防火墙..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
elif command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
fi

systemctl restart nginx

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"
echo ""
echo "📝 后续步骤:"
echo "  1. 编辑 .env.production 添加 LLM API 密钥"
echo "  2. 配置 SSL 证书: certbot --nginx -d $DOMAIN"
echo "  3. 重启服务: docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "🔍 查看日志:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🌐 访问地址:"
echo "  https://$DOMAIN"
echo ""
