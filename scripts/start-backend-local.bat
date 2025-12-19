@echo off
REM Data Agent V4 - 后端本地启动脚本
REM 用途: 在本地运行后端服务（不使用Docker）

echo ========================================
echo Data Agent V4 - 后端本地启动
echo ========================================
echo.

REM 检查Python环境
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
python --version
echo.

REM 检查基础设施服务
echo [2/5] 检查基础设施服务...
docker-compose ps | findstr "postgres" >nul
if %errorlevel% neq 0 (
    echo [INFO] 启动基础设施服务（数据库、MinIO、ChromaDB）...
    docker-compose up -d db storage vector_db
    echo [INFO] 等待服务启动...
    timeout /t 10 /nobreak >nul
)
echo [OK] 基础设施服务正在运行
echo.

REM 进入后端目录
cd backend

REM 检查虚拟环境
echo [3/5] 检查Python虚拟环境...
if not exist "venv" (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
)
echo [OK] 虚拟环境已准备
echo.

REM 激活虚拟环境并安装依赖
echo [4/5] 安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)
echo.

REM 检查环境变量
if not exist ".env" (
    echo [WARN] 未找到 .env 文件，请确保根目录有 .env 配置
    echo [INFO] 使用默认配置...
)

REM 启动后端服务
echo [5/5] 启动后端服务...
echo.
echo ========================================
echo 后端服务启动中...
echo ========================================
echo.
echo 访问地址:
echo   - API文档:     http://localhost:8004/docs
echo   - 健康检查:    http://localhost:8004/health
echo   - API根路径:   http://localhost:8004/api/v1
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

REM 🔥 Token Expansion: 增加 --timeout-keep-alive 到 300 秒以支持长文本生成
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004 --timeout-keep-alive 300

