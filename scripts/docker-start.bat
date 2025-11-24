@echo off
REM =============================================================================
REM Data Agent V4 - Docker启动脚本 (Windows版本)
REM =============================================================================

setlocal enabledelayedexpansion

REM 获取脚本目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM 打印标题
echo ===============================================================================
echo  Data Agent V4 - Docker环境启动脚本 (Windows)
echo  Docker Environment Startup Script (Windows)
echo ===============================================================================
echo.

REM 检查Docker是否安装和运行
echo [INFO] 检查Docker环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker未安装，请先安装Docker Desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker守护进程未运行，请启动Docker Desktop
    pause
    exit /b 1
)

echo [SUCCESS] Docker环境正常

REM 检查Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    set DOCKER_COMPOSE_CMD=docker compose
) else (
    set DOCKER_COMPOSE_CMD=docker-compose
)

echo [INFO] 使用命令: %DOCKER_COMPOSE_CMD%

REM 检查环境变量文件
echo [INFO] 检查环境变量配置...

if not exist "%PROJECT_ROOT%\.env" (
    echo [WARNING] .env文件不存在

    if exist "%PROJECT_ROOT%\.env.example" (
        echo [INFO] 从.env.example创建.env文件...
        copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
        echo [SUCCESS] 已创建.env文件
        echo [WARNING] 请编辑.env文件并配置真实的API密钥和密码
    ) else (
        echo [ERROR] .env.example文件不存在
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] .env文件已存在
)

REM 检查关键环境变量
findstr /C:"your_zhipuai_api_key_here" "%PROJECT_ROOT%\.env" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] 请配置真实的ZHIPUAI_API_KEY
)

findstr /C:"your-super-secret-key" "%PROJECT_ROOT%\.env" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] 请配置强密码SECRET_KEY
)

echo [SUCCESS] 环境变量文件检查完成

REM 创建必要的目录
echo [INFO] 创建必要的目录...

if not exist "%PROJECT_ROOT%\backend\logs" mkdir "%PROJECT_ROOT%\backend\logs"
if not exist "%PROJECT_ROOT%\backend\uploads" mkdir "%PROJECT_ROOT%\backend\uploads"
if not exist "%PROJECT_ROOT%\backend\temp" mkdir "%PROJECT_ROOT%\backend\temp"
if not exist "%PROJECT_ROOT%\frontend\logs" mkdir "%PROJECT_ROOT%\frontend\logs"
if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if not exist "%PROJECT_ROOT%\data\postgres" mkdir "%PROJECT_ROOT%\data\postgres"
if not exist "%PROJECT_ROOT%\data\minio" mkdir "%PROJECT_ROOT%\data\minio"
if not exist "%PROJECT_ROOT%\data\chroma" mkdir "%PROJECT_ROOT%\data\chroma"

echo [SUCCESS] 目录创建完成

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

REM 解析命令行参数
set REBUILD=false
set SKIP_BUILD=false
set VALIDATE_ONLY=false

:parse_args
if "%~1"=="" goto end_parse_args
if "%~1"=="--rebuild" (
    set REBUILD=true
    shift
    goto parse_args
)
if "%~1"=="--skip-build" (
    set SKIP_BUILD=true
    shift
    goto parse_args
)
if "%~1"=="--validate-only" (
    set VALIDATE_ONLY=true
    shift
    goto parse_args
)
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
echo [ERROR] 未知参数: %~1
pause
exit /b 1

:show_help
echo 用法: %~nx0 [选项]
echo.
echo 选项:
echo   --rebuild        强制重新构建所有镜像
echo   --skip-build     跳过镜像构建
echo   --validate-only  仅验证配置，不启动服务
echo   --help, -h       显示此帮助信息
echo.
pause
exit /b 0

:end_parse_args

REM 仅验证配置
if "%VALIDATE_ONLY%"=="true" (
    echo [INFO] 验证配置...
    if exist "%PROJECT_ROOT%\scripts\validate-docker-config.py" (
        python "%PROJECT_ROOT%\scripts\validate-docker-config.py" --env-file .env
    ) else (
        echo [WARNING] 配置验证脚本不存在，跳过验证
    )
    pause
    exit /b 0
)

REM 验证配置
if exist "%PROJECT_ROOT%\scripts\validate-docker-config.py" (
    echo [INFO] 验证配置...
    python "%PROJECT_ROOT%\scripts\validate-docker-config.py" --env-file .env
    echo.
)

REM 构建镜像
if "%SKIP_BUILD%"=="false" (
    echo [INFO] 构建Docker镜像...
    if "%REBUILD%"=="true" (
        echo [INFO] 强制重新构建所有镜像...
        %DOCKER_COMPOSE_CMD% build --no-cache
    ) else (
        %DOCKER_COMPOSE_CMD% build
    )

    if errorlevel 1 (
        echo [ERROR] Docker镜像构建失败
        pause
        exit /b 1
    )
    echo [SUCCESS] Docker镜像构建完成
) else (
    echo [INFO] 跳过镜像构建
)

REM 启动服务
echo [INFO] 启动Docker服务...
%DOCKER_COMPOSE_CMD% up -d

if errorlevel 1 (
    echo [ERROR] Docker服务启动失败
    pause
    exit /b 1
)

echo [SUCCESS] Docker服务启动成功

REM 等待服务就绪
echo [INFO] 等待服务就绪...

echo [INFO] 等待PostgreSQL数据库启动...
timeout /t 10 /nobreak >nul

echo [INFO] 等待后端API服务启动...
timeout /t 15 /nobreak >nul

echo [INFO] 等待前端服务启动...
timeout /t 15 /nobreak >nul

REM 显示服务状态
echo.
echo [INFO] 服务状态:
echo.
%DOCKER_COMPOSE_CMD% ps

echo.
echo [INFO] 服务访问地址:
echo   前端应用:    http://localhost:3000
echo   后端API:     http://localhost:8004
echo   API文档:     http://localhost:8004/docs
echo   MinIO控制台: http://localhost:9001
echo   ChromaDB:    http://localhost:8001
echo.

REM 显示有用的命令
echo [INFO] 常用命令:
echo   查看日志:     %DOCKER_COMPOSE_CMD% logs -f [service_name]
echo   停止服务:     %DOCKER_COMPOSE_CMD% down
echo   重启服务:     %DOCKER_COMPOSE_CMD% restart [service_name]
echo   进入后端容器: docker exec -it dataagent-backend bash
echo   数据库连接:   docker exec -it dataagent-postgres psql -U postgres -d dataagent
echo.

echo [SUCCESS] Data Agent V4 Docker环境启动完成！
echo [INFO] 如果遇到问题，请查看日志: %DOCKER_COMPOSE_CMD% logs -f
echo.

pause