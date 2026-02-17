@echo off
REM 后端日志捕获脚本
REM 用法: 运行此脚本 -> 前端操作 -> 按 Ctrl+C 保存日志

echo ========================================
echo    Data Agent 后端日志捕获工具
echo ========================================
echo.
echo [1/3] 清空旧日志备份...
if exist logs\debug_session.log (
    move /Y logs\debug_session.log logs\debug_session_old.log 2>nul
)

echo [2/3] 开始捕获后端日志...
echo       前端执行你的操作，完成后按 Ctrl+C
echo.
echo ========================================
echo.

REM 捕获 Docker 日志，带上时间戳
docker logs -f dataagent-backend --tail 0 2>&1 | findstr /V "^\s*$" > logs\debug_session.log

echo.
echo ========================================
echo [3/3] 日志已保存到: backend\logs\debug_session.log
echo ========================================
pause
