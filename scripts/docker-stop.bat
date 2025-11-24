@echo off
REM =============================================================================
REM Data Agent V4 - Docker停止脚本 (Windows版本)
REM =============================================================================

setlocal enabledelayedexpansion

REM 获取脚本目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM 打印标题
echo ===============================================================================
echo  Data Agent V4 - Docker环境停止脚本 (Windows)
echo  Docker Environment Stop Script (Windows)
echo ===============================================================================
echo.

REM 检查Docker Compose命令
docker-compose --version >nul 2>&1
if errorlevel 1 (
    set DOCKER_COMPOSE_CMD=docker compose
) else (
    set DOCKER_COMPOSE_CMD=docker-compose
)

REM 解析命令行参数
set CLEANUP=false

:parse_args
if "%~1"=="" goto end_parse_args
if "%~1"=="--cleanup" (
    set CLEANUP=true
    shift
    goto parse_args
)
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
echo [ERROR] 未知参数: %~1
goto show_help

:show_help
echo 用法: %~nx0 [选项]
echo.
echo 选项:
echo   --cleanup    停止服务并清理所有相关资源（包括数据卷）
echo   --help, -h   显示此帮助信息
echo.
echo 注意: 使用--cleanup会删除所有数据，请谨慎使用！
pause
exit /b 0

:end_parse_args

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

REM 停止服务
echo [INFO] 停止Docker服务...
%DOCKER_COMPOSE_CMD% down

if errorlevel 1 (
    echo [WARNING] 停止服务时出现警告（可能服务未运行）
) else (
    echo [SUCCESS] Docker服务已停止
)

REM 清理资源（如果指定）
if "%CLEANUP%"=="true" (
    echo [WARNING] 警告: 这将删除所有数据卷，包括数据库数据！
    set /p confirm="确定要继续吗？(y/N): "

    if /i "!confirm!"=="y" (
        echo [INFO] 清理Docker资源...
        %DOCKER_COMPOSE_CMD% down -v --remove-orphans
        docker image prune -f
        echo [SUCCESS] Docker资源清理完成
    ) else (
        echo [INFO] 已取消清理操作
    )
)

echo [SUCCESS] Data Agent V4 Docker环境已停止
echo.

pause