@echo off
REM ============================================================================
REM Data Agent V4 - 完整本地启动脚本
REM ============================================================================
REM 用途: 在本地虚拟环境中启动前后端服务（不使用Docker）
REM 前提: 需要先启动基础设施服务（PostgreSQL, MinIO, ChromaDB）
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo                    Data Agent V4 - 本地开发环境启动
echo ============================================================================
echo.

REM ============================================================================
REM 步骤 1: 环境检查
REM ============================================================================
echo [步骤 1/6] 检查开发环境...
echo.

REM 检查Python
echo [1.1] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION%
echo.

REM 检查Node.js
echo [1.2] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到Node.js，请先安装Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION%
echo.

REM 检查Docker
echo [1.3] 检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到Docker，请先安装Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('docker --version') do set DOCKER_VERSION=%%i
echo [OK] %DOCKER_VERSION%
echo.

REM ============================================================================
REM 步骤 2: 启动基础设施服务
REM ============================================================================
echo [步骤 2/6] 启动基础设施服务（PostgreSQL, MinIO, ChromaDB）...
echo.

docker-compose ps | findstr "postgres" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 启动基础设施服务...
    docker-compose up -d db storage vector_db
    echo [INFO] 等待服务启动（15秒）...
    timeout /t 15 /nobreak >nul
) else (
    echo [OK] 基础设施服务已在运行
)
echo.

REM ============================================================================
REM 步骤 3: 准备后端环境
REM ============================================================================
echo [步骤 3/6] 准备后端Python虚拟环境...
echo.

cd backend

REM 创建虚拟环境
if not exist "venv" (
    echo [INFO] 创建Python虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] 虚拟环境创建失败
        cd ..
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建成功
) else (
    echo [OK] 虚拟环境已存在
)
echo.

REM 激活虚拟环境并安装依赖
echo [INFO] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] 后端依赖安装失败
    cd ..
    pause
    exit /b 1
)
echo [OK] 后端依赖安装完成
echo.

cd ..

REM ============================================================================
REM 步骤 4: 准备前端环境
REM ============================================================================
echo [步骤 4/6] 准备前端Node.js环境...
echo.

cd frontend

REM 安装依赖
if not exist "node_modules" (
    echo [INFO] 安装前端依赖（首次运行可能需要几分钟）...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] 前端依赖安装失败
        cd ..
        pause
        exit /b 1
    )
    echo [OK] 前端依赖安装完成
) else (
    echo [OK] 前端依赖已安装
)
echo.

REM 创建环境配置
if not exist ".env.local" (
    echo [INFO] 创建前端环境配置...
    (
        echo NEXT_PUBLIC_API_URL=http://localhost:8004/api/v1
        echo NEXT_PUBLIC_APP_NAME=Data Agent V4
        echo NODE_ENV=development
    ) > .env.local
    echo [OK] 环境配置已创建
) else (
    echo [OK] 环境配置已存在
)
echo.

cd ..

REM ============================================================================
REM 步骤 5: 启动服务
REM ============================================================================
echo [步骤 5/6] 启动前后端服务...
echo.
echo ============================================================================
echo 正在启动服务，请稍候...
echo ============================================================================
echo.

REM 启动后端（在新窗口）
echo [INFO] 启动后端服务（新窗口）...
start "Data Agent V4 - Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004"
timeout /t 5 /nobreak >nul

REM 启动前端（在新窗口）
echo [INFO] 启动前端服务（新窗口）...
start "Data Agent V4 - Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ============================================================================
echo [步骤 6/6] 服务启动完成！
echo ============================================================================
echo.
echo 📊 服务访问地址:
echo.
echo 前端服务:
echo   🌐 主页:        http://localhost:3000
echo   💬 聊天界面:    http://localhost:3000/chat
echo   📁 数据源管理:  http://localhost:3000/data-sources
echo   📄 文档管理:    http://localhost:3000/documents
echo.
echo 后端服务:
echo   📖 API文档:     http://localhost:8004/docs
echo   ✅ 健康检查:    http://localhost:8004/health
echo   🔌 API根路径:   http://localhost:8004/api/v1
echo.
echo 基础设施服务:
echo   🗄️  PostgreSQL:  localhost:5432
echo   📦 MinIO API:   http://localhost:9000
echo   🎨 MinIO UI:    http://localhost:9001
echo   🔍 ChromaDB:    http://localhost:8001
echo.
echo ============================================================================
echo 💡 提示:
echo   - 前后端服务在独立窗口中运行
echo   - 关闭窗口或按 Ctrl+C 可停止对应服务
echo   - 查看各窗口的日志输出以监控服务状态
echo   - 停止所有服务: 关闭所有窗口 + docker-compose down
echo ============================================================================
echo.
pause

