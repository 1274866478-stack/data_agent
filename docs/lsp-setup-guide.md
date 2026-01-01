# LSP服务器安装指南

> **已创建配置文件**: `.vscode/settings.json`, `.vscode/extensions.json`, `.vscode/launch.json`

---

## 🚀 快速开始

### 方式1: 使用安装脚本 (推荐)

**Windows PowerShell:**
```powershell
# 右键PowerShell以管理员身份运行
cd C:\data_agent
.\scripts\install-lsp.ps1
```

**Git Bash / WSL:**
```bash
cd /c/data_agent
chmod +x scripts/install-lsp.sh
./scripts/install-lsp.sh
```

### 方式2: 手动安装

如果脚本安装失败，可以手动执行以下命令：

---

## 📦 需要安装的LSP服务器

### 1. Python LSP (后端开发)

#### 推荐选项A: Pyright (官方推荐)
```bash
npm install -g pyright
```

#### 选项B: Pylsp (Python语言服务器)
```bash
pip install python-lsp-server
```

#### Python格式化工具
```bash
pip install black isort flake8 mypy
```

---

### 2. TypeScript/JavaScript LSP (前端开发)

#### 选项A: TypeScript Language Server
```bash
npm install -g typescript-language-server
```

#### 选项B: vtsls (更快，推荐)
```bash
npm install -g vtsls
```

#### 前端代码检查和格式化
```bash
npm install -g eslint prettier
```

---

## 🔧 VS Code配置

已自动创建以下配置文件：

### `.vscode/settings.json`
- Python解释器路径配置
- TypeScript SDK路径配置
- 格式化和代码检查规则
- 文件关联和排除规则

### `.vscode/extensions.json`
推荐的VS Code扩展列表，包括：
- Python核心扩展 (Pyright, Black, Flake8)
- TypeScript/JavaScript扩展 (ESLint, Prettier, TailwindCSS)
- Docker和数据库扩展
- Git增强工具

### `.vscode/launch.json`
调试配置，支持：
- FastAPI后端调试
- Next.js前端调试
- Pytest单元测试调试

---

## ✅ 验证安装

### 1. 检查Python LSP
1. 打开VS Code
2. 打开任意 `.py` 文件 (如 `backend/src/app/main.py`)
3. 查看右下角是否显示 "Pyright" 或 "Pylance"
4. 输入代码，查看是否有智能提示

### 2. 检查TypeScript LSP
1. 打开任意 `.tsx` 文件 (如 `frontend/src/app/page.tsx`)
2. 查看右下角是否显示 "TypeScript JS"
3. 输入代码，查看是否有智能提示

### 3. 使用LSP工具测试
在VS Code中打开命令面板 (Ctrl+Shift+P)，输入：
- `Python: Select Interpreter` - 选择Python解释器
- `Python: Run Linting` - 运行代码检查
- `TypeScript: Restart TS Server` - 重启TS服务器

---

## 🛠️ 常见问题

### Q1: Pyright无法识别Python虚拟环境
**解决方案**:
1. 按 `Ctrl+Shift+P`
2. 输入 `Python: Select Interpreter`
3. 选择 `backend\.venv\Scripts\python.exe`

### Q2: TypeScript语言服务器报错
**解决方案**:
1. 确保已安装前端依赖: `cd frontend && npm install`
2. 按 `Ctrl+Shift+P`
3. 输入 `TypeScript: Restart TS Server`

### Q3: 格式化工具不工作
**解决方案**:
1. 检查是否安装了对应的格式化工具
2. 打开VS Code设置 (Ctrl+,)
3. 搜索 `format on save`，确保已启用

### Q4: LSP服务器响应慢
**解决方案**:
1. 对于Python: 使用 `basedpyright` 替代 `pyright` (更快)
   ```bash
   pip install basedpyright
   ```
2. 对于TypeScript: 使用 `vtsls` 替代 `typescript-language-server`
   ```bash
   npm install -g vtsls
   ```

---

## 📋 检查清单

安装完成后，请确认以下项目：

- [ ] VS Code已安装推荐的扩展 (查看扩展 -> 推荐扩展)
- [ ] Python文件可以正常显示智能提示
- [ ] TypeScript文件可以正常显示智能提示
- [ ] 保存时自动格式化工作正常
- [ ] 可以正常调试后端 (FastAPI)
- [ ] 可以正常调试前端 (Next.js)

---

## 📞 需要帮助？

如果遇到问题，请检查：
1. Python版本 >= 3.8 (运行 `python --version`)
2. Node.js版本 >= 18 (运行 `node --version`)
3. 虚拟环境已激活 (Windows: `backend\.venv\Scripts\Activate.ps1`)
4. 前端依赖已安装 (`cd frontend && npm install`)

---

**生成时间**: 2025-01-01
**项目**: Data Agent V4
**版本**: 1.0.0
