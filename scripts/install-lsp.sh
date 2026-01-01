#!/bin/bash
# LSP服务器和开发工具安装脚本 (Linux/Git Bash/WSL)
# 使用方法: chmod +x scripts/install-lsp.sh && ./scripts/install-lsp.sh

set -e  # 遇到错误立即退出

echo "========================================"
echo "Data Agent V4 - LSP服务器安装工具"
echo "========================================"
echo ""

# ==================== Python LSP服务器 ====================
echo "[1/4] 安装Python LSP服务器..."

echo "  - 安装 Pyright (推荐)..."
npm install -g pyright

echo "  - 安装 Python LSP Server (可选)..."
pip install python-lsp-server

echo "  - 安装 Black (格式化工具)..."
pip install black

echo "  - 安装 isort (import排序)..."
pip install isort

echo "  - 安装 flake8 (linting)..."
pip install flake8

echo "  - 安装 mypy (类型检查)..."
pip install mypy

# ==================== TypeScript/JavaScript LSP服务器 ====================
echo "[2/4] 安装TypeScript/JavaScript LSP服务器..."

echo "  - 安装 TypeScript Language Server..."
npm install -g typescript-language-server

echo "  - 安装 vtsls (更快的替代，可选)..."
npm install -g vtsls

echo "  - 安装 ESLint..."
npm install -g eslint

echo "  - 安装 Prettier..."
npm install -g prettier

# ==================== Python开发依赖 ====================
echo "[3/4] 安装Python开发依赖..."

if [ -f "backend/requirements.txt" ]; then
    echo "  - 从 requirements.txt 安装..."
    backend/.venv/Scripts/python.exe -m pip install --upgrade pip
    backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
else
    echo "  ⚠️  未找到 backend/requirements.txt"
fi

# ==================== 前端依赖 ====================
echo "[4/4] 安装前端依赖..."

if [ -f "frontend/package.json" ]; then
    echo "  - 从 package.json 安装..."
    cd frontend
    npm install
    cd ..
else
    echo "  ⚠️  未找到 frontend/package.json"
fi

# ==================== VS Code扩展安装 ====================
echo ""
echo "[额外] 安装VS Code推荐扩展..."
echo "  请在VS Code中按 Ctrl+Shift+P，输入 'Extensions: Show Recommended Extensions'"
echo "  或使用命令: code --install-extension ms-python.python"

# ==================== 完成 ====================
echo ""
echo "========================================"
echo "✅ 安装完成！"
echo "========================================"
echo ""
echo "后续步骤:"
echo "1. 重新加载VS Code窗口 (Ctrl+Shift+P -> 'Reload Window')"
echo "2. 检查LSP状态: Ctrl+Shift+P -> 'Python: Select Interpreter'"
echo "3. 测试Python类型检查: 打开任意.py文件查看智能提示"
echo "4. 测试TypeScript类型检查: 打开任意.tsx文件查看智能提示"
echo ""
echo "如遇到问题，请检查:"
echo "- Python路径: ${workspaceFolder}/backend/.venv/Scripts/python.exe"
echo "- Node.js版本: node --version (建议 >= 18)"
echo "- Python版本: python --version (建议 >= 3.8)"
