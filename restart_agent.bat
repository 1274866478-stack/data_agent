@echo off
REM ============================================================================
REM Data Agent V4 - Agent服务重启脚本
REM ============================================================================

echo.
echo ============================================================================
echo                    重启Agent服务 (应用Bug修复)
echo ============================================================================
echo.

echo [步骤 1/3] 停止当前Agent服务...
echo.

REM 停止占用8004端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8004" ^| findstr "LISTENING"') do (
    echo   停止进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [步骤 2/3] 等待端口释放...
timeout /t 3 /nobreak >nul

echo.
echo [步骤 3/3] 重新启动Agent服务...
echo.

REM 启动后端服务
cd backend
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo   启动后端服务 (端口8004)...
    start "Data Agent V4 - Backend" cmd /k "uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004 --timeout-keep-alive 300"
    cd ..
) else (
    echo   [ERROR] 虚拟环境不存在，请先运行 scripts\start-all-local.bat
    cd ..
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo                         Agent服务已重启
echo ============================================================================
echo.
echo   - 后端API: http://localhost:8004/api/v1
echo   - API文档: http://localhost:8004/docs
echo.
echo   Bug修复已应用:
echo   1. AI现在必须先调用 list_tables() 才能生成SQL
echo   2. 检测并修正假设表名错误 (sales, orders等)
echo   3. 会话级表名缓存减少重复调用
echo.
echo ============================================================================

timeout /t 5 /nobreak >nul
