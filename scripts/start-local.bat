@echo off
REM Data Agent V4 - 本地启动脚本
REM 用途: 在本地运行前端服务（后端使用Docker）

echo ========================================
echo Data Agent V4 - 本地启动
echo ========================================
echo.

REM 检查后端服务状态
echo [1/4] 检查后端服务状态...
docker-compose ps | findstr "backend" >nul
if %errorlevel% equ 0 (
    echo [OK] 后端服务正在运行
) else (
    echo [WARN] 后端服务未运行，正在启动...
    docker-compose up -d backend db storage vector_db
    timeout /t 5 /nobreak >nul
)
echo.

REM 进入前端目录
cd frontend

REM 检查依赖
echo [2/4] 检查前端依赖...
if not exist "node_modules" (
    echo [INFO] 首次运行，正在安装依赖...
    echo 这可能需要几分钟时间，请耐心等待...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [OK] 依赖已安装
)
echo.

REM 检查环境变量
echo [3/4] 检查环境配置...
if not exist ".env.local" (
    echo [INFO] 创建 .env.local 文件...
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

REM 启动前端服务
echo [4/4] 启动前端开发服务器...
echo.
echo ========================================
echo 前端服务启动中...
echo ========================================
echo.
echo 访问地址:
echo   - 主页:        http://localhost:3000
echo   - 聊天界面:    http://localhost:3000/chat
echo   - 数据源管理:  http://localhost:3000/data-sources
echo   - 文档管理:    http://localhost:3000/documents
echo.
echo 后端服务:
echo   - API文档:     http://localhost:8004/docs
echo   - 健康检查:    http://localhost:8004/health
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

call npm run dev

