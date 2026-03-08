#!/bin/bash
# 腾讯云部署打包脚本
# 排除不必要文件，生成部署包

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_FILE="${PROJECT_ROOT}/insight-agent-deploy.tar.gz"
DEPLOY_DIR="insight-agent-deploy"

echo "📦 开始打包项目..."
echo "项目根目录: ${PROJECT_ROOT}"

# 清理旧文件
if [ -f "$DEPLOY_FILE" ]; then
    echo "🗑️  删除旧部署包: $DEPLOY_FILE"
    rm -f "$DEPLOY_FILE"
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

# 复制必要文件
echo "📋 复制项目文件..."

# 核心目录
mkdir -p "${TEMP_DIR}/${DEPLOY_DIR}"
cp -r "${PROJECT_ROOT}/backend" "${TEMP_DIR}/${DEPLOY_DIR}/"
cp -r "${PROJECT_ROOT}/frontend" "${TEMP_DIR}/${DEPLOY_DIR}/"
cp -r "${PROJECT_ROOT}/Agent" "${TEMP_DIR}/${DEPLOY_DIR}/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/AgentV2" "${TEMP_DIR}/${DEPLOY_DIR}/" 2>/dev/null || true
cp -r "${PROJECT_ROOT}/scripts" "${TEMP_DIR}/${DEPLOY_DIR}/"

# 配置文件
cp "${PROJECT_ROOT}/docker-compose.prod.yml" "${TEMP_DIR}/${DEPLOY_DIR}/"
cp "${PROJECT_ROOT}/.env.production" "${TEMP_DIR}/${DEPLOY_DIR}/" 2>/dev/null || echo "# .env.production 将在服务器上生成" > "${TEMP_DIR}/${DEPLOY_DIR}/.env.production"
cp "${PROJECT_ROOT}/.dockerignore" "${TEMP_DIR}/${DEPLOY_DIR}/" 2>/dev/null || true

# 创建 nginx 目录
mkdir -p "${TEMP_DIR}/${DEPLOY_DIR}/nginx"
if [ -f "${PROJECT_ROOT}/nginx.conf" ]; then
    cp "${PROJECT_ROOT}/nginx.conf" "${TEMP_DIR}/${DEPLOY_DIR}/nginx/"
fi

# 创建 Dockerfiles
for dockerfile in "${PROJECT_ROOT}"/Dockerfile* "${PROJECT_ROOT}"/backend/Dockerfile* "${PROJECT_ROOT}"/frontend/Dockerfile* "${PROJECT_ROOT}"/Agent/Dockerfile*; do
    if [ -f "$dockerfile" ]; then
        dir=$(dirname "$dockerfile")
        filename=$(basename "$dockerfile")
        mkdir -p "${TEMP_DIR}/${DEPLOY_DIR}/${dir}"
        cp "$dockerfile" "${TEMP_DIR}/${DEPLOY_DIR}/${dir}/"
    fi
done

# 清理不必要文件
echo "🧹 清理不必要文件..."
find "${TEMP_DIR}/${DEPLOY_DIR}" -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type d -name ".venv" -o -name "venv" | xargs rm -rf 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type d -name ".git" -exec rm -rf {} + 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type f -name ".DS_Store" -delete 2>/dev/null || true
find "${TEMP_DIR}/${DEPLOY_DIR}" -type f -name "*.log" -delete 2>/dev/null || true

# 打包
echo "📦 压缩打包..."
cd "${TEMP_DIR}"
tar -czf "$DEPLOY_FILE" "$DEPLOY_DIR"

# 获取文件大小
FILE_SIZE=$(du -h "$DEPLOY_FILE" | cut -f1)

echo ""
echo "✅ 打包完成!"
echo "📁 部署包: $DEPLOY_FILE"
echo "📊 文件大小: $FILE_SIZE"
echo ""
echo "💡 下一步: 执行 bash scripts/upload-to-server.sh"
