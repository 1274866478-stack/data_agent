#!/bin/bash
# 上传部署包到腾讯云服务器

set -e

# 服务器配置
SERVER_IP="101.35.226.59"
SERVER_USER="ubuntu"
REMOTE_DIR="/home/ubuntu"
DEPLOY_FILE="./insight-agent-deploy.tar.gz"

echo "📤 开始上传部署包..."
echo "服务器: ${SERVER_USER}@${SERVER_IP}"
echo "远程目录: ${REMOTE_DIR}"

# 检查本地文件
if [ ! -f "$DEPLOY_FILE" ]; then
    echo "❌ 错误: 部署包不存在: $DEPLOY_FILE"
    echo "💡 请先执行: bash scripts/package-for-deploy.sh"
    exit 1
fi

# 获取文件大小
FILE_SIZE=$(du -h "$DEPLOY_FILE" | cut -f1)
echo "📊 文件大小: $FILE_SIZE"

# 上传文件
echo "🚀 正在上传..."
scp "$DEPLOY_FILE" "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/"

echo ""
echo "✅ 上传完成!"
echo ""
echo "💡 下一步:"
echo "   1. ssh ${SERVER_USER}@${SERVER_IP}"
echo "   2. cd /opt && sudo mkdir -p bichat"
echo "   3. sudo tar -xzf ${REMOTE_DIR}/insight-agent-deploy.tar.gz -C /opt/"
echo "   4. cd /opt/insight-agent-deploy && sudo bash scripts/deploy-on-server.sh"
