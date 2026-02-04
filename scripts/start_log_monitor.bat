@echo off
REM 后台日志监控服务启动脚本
REM 用法: 运行此脚本启动日志监控，按 Ctrl+C 停止

echo ========================================
echo    Data Agent 后台日志监控服务
echo ========================================
echo.
echo [功能]
echo   - 监控 backend/logs/ 目录下的日志文件
echo   - 将新日志追加到 logs/ai_accessible_logs.jsonl
echo   - 将新日志追加到 AgentV2/knowledge/logs/{date}.jsonl
echo.
echo [选项]
echo   1. 持续监控（默认）
echo   2. 单次检查
echo.
set /p choice="请选择 (1 或 2): "

if "%choice%"=="2" (
    echo.
    echo [执行] 单次检查模式
    echo.
    python scripts\monitor_backend_logs.py --once
) else (
    echo.
    echo [执行] 持续监控模式
    echo        按 Ctrl+C 停止
    echo.
    python scripts\monitor_backend_logs.py
)

echo.
echo ========================================
echo    监控服务已停止
echo ========================================
pause
