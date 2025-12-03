#!/bin/bash

# Frontend 清理脚本
# 清理不必要的文件，保持项目结构整洁

echo "🧹 开始清理前端项目..."

# 清理构建缓存
echo "清理构建缓存..."
rm -rf .next
rm -rf node_modules/.cache

# 清理测试覆盖率报告
echo "清理测试覆盖率报告..."
rm -rf coverage/

# 清理TypeScript构建输出
echo "清理TypeScript输出..."
rm -rf dist/
rm -rf build/

# 清理日志文件
echo "清理日志文件..."
find . -name "*.log" -type f -delete
find . -name "npm-debug.log*" -type f -delete
find . -name "yarn-debug.log*" -type f -delete
find . -name "yarn-error.log*" -type f -delete

# 清理临时文件
echo "清理临时文件..."
find . -name ".DS_Store" -type f -delete
find . -name "Thumbs.db" -type f -delete

echo "✅ 清理完成！"
echo ""
echo "💡 提示：如果需要重新安装依赖，请运行："
echo "   npm install"
echo ""
echo "💡 如果需要重新构建，请运行："
echo "   npm run build"