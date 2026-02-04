@echo off
REM 清空日志文件脚本

echo ========================================
echo    Data Agent 日志清理工具
echo ========================================
echo.

REM 列出当前日志文件
echo [当前日志文件]
dir /s backend\logs\*.log 2>nul | find "个文件"
if exist logs\ai_accessible_logs.jsonl (
    echo logs\ai_accessible_logs.jsonl
)
if exist AgentV2\knowledge\logs (
    dir /s AgentV2\knowledge\logs 2>nul | find "个文件"
)

echo.
echo ========================================
echo 清空选项:
echo   1. 只清空后端日志 (backend/logs/)
echo   2. 清空所有日志
echo   3. 取消
echo ========================================

set /p choice="请选择 (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo [清空] 后端日志文件...
    break> backend\logs\application.log 2>nul
    break> backend\logs\error.log 2>nul
    break> backend\logs\debug.log 2>nul
    break> backend\logs\agent.log 2>nul
    for %%f in (backend\logs\agent_*.log) do break> "%%f" 2>nul
    echo ✅ 后端日志已清空
) else if "%choice%"=="2" (
    echo.
    echo [清空] 后端日志文件...
    break> backend\logs\application.log 2>nul
    break> backend\logs\error.log 2>nul
    break> backend\logs\debug.log 2>nul
    break> backend\logs\agent.log 2>nul
    for %%f in (backend\logs\agent_*.log) do break> "%%f" 2>nul

    echo [清空] AI可访问日志...
    break> logs\ai_accessible_logs.jsonl 2>nul

    echo [清空] 知识库日志...
    if exist AgentV2\knowledge\logs (
        rmdir /s /q AgentV2\knowledge\logs 2>nul
    )

    echo [清空] 监控位置记录...
    break> logs\.monitor_positions.json 2>nul

    echo ✅ 所有日志已清空
) else (
    echo 已取消
)

echo.
pause
