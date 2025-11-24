@echo off
REM ============================================================================
REM Data Agent V4 - 混合模式启动脚本
REM ============================================================================
REM 用途: 后端使用Docker，前端使用本地Node.js（推荐开发模式）
REM 优点: 前端热重载快，后端依赖问题少
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo              Data Agent V4 - 混合模式启动 (推荐)
echo ============================================================================
echo.
echo 模式说明:
echo   - 后端: Docker容器运行 (避免Python依赖问题)
echo   - 前端: 本地npm运行 (热重载更快)
echo   - 基础设施: Docker容器运行 (PostgreSQL, MinIO, ChromaDB)
echo.
echo ============================================================================
echo.

REM ============================================================================
REM 步骤 1: 环境检查
REM ============================================================================
echo [步骤 1/5] 检查开发环境...
echo.

REM 检查Node.js
echo [1.1] 检查Node.js环境...
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
echo [1.2] 检查Docker环境...
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
REM 步骤 2: 启动Docker服务
REM ============================================================================
echo [步骤 2/5] 启动Docker服务...
echo.

echo [INFO] 启动后端和基础设施服务...
docker-compose up -d backend db storage vector_db
if %errorlevel% neq 0 (
    echo [ERROR] Docker服务启动失败
    pause
    exit /b 1
)
echo [OK] Docker服务启动成功
echo.

echo [INFO] 等待服务初始化（15秒）...
timeout /t 15 /nobreak >nul
echo.

REM ============================================================================
REM 步骤 3: 准备前端环境
REM ============================================================================
echo [步骤 3/5] 准备前端环境...
echo.

cd frontend

REM 检查依赖
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
REM 步骤 4: 验证服务状态
REM ============================================================================
echo [步骤 4/5] 验证服务状态...
echo.

echo [INFO] 检查Docker服务状态...
docker-compose ps
echo.

echo [INFO] 检查后端健康状态...
curl -s http://localhost:8004/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 后端服务响应正常
) else (
    echo [WARN] 后端服务可能还在启动中，请稍后访问
)
echo.

REM ============================================================================
REM 步骤 5: 启动前端服务
REM ============================================================================
echo [步骤 5/5] 启动前端服务...
echo.
echo ============================================================================
echo 正在启动前端开发服务器...
echo ============================================================================
echo.

REM 启动前端（在当前窗口）
cd frontend
echo [INFO] 前端服务启动中，请稍候...
echo.
echo ============================================================================
echo 📊 服务访问地址:
echo ============================================================================
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
echo   - 前端在当前窗口运行，按 Ctrl+C 停止
echo   - 后端在Docker容器中运行
echo   - 停止所有服务: Ctrl+C (前端) + docker-compose down (后端)
echo   - 查看后端日志: docker logs dataagent-backend -f
echo ============================================================================
echo.

call npm run dev

