@echo off
REM Data Agent V4 - 功能测试脚本 (Windows版本)
REM 用途: 快速测试所有核心功能

setlocal enabledelayedexpansion

set API_URL=http://localhost:8004
set FRONTEND_URL=http://localhost:3000

echo ========================================
echo Data Agent V4 - 功能测试
echo ========================================
echo.

REM 1. 健康检查
echo [1/8] 测试后端健康检查...
curl -s "%API_URL%/health" > temp_health.json
findstr /C:"healthy" temp_health.json >nul
if %errorlevel% equ 0 (
    echo [OK] 后端服务健康
) else (
    echo [ERROR] 后端服务异常
    del temp_health.json
    exit /b 1
)
del temp_health.json
echo.

REM 2. Ping测试
echo [2/8] 测试Ping端点...
curl -s "%API_URL%/api/v1/health/ping" > temp_ping.json
findstr /C:"pong" temp_ping.json >nul
if %errorlevel% equ 0 (
    echo [OK] Ping测试通过
) else (
    echo [ERROR] Ping测试失败
)
del temp_ping.json
echo.

REM 3. 服务状态检查
echo [3/8] 检查所有服务状态...
curl -s "%API_URL%/api/v1/health/services"
echo.
echo.

REM 4. 测试租户创建
echo [4/8] 测试租户创建...
curl -s -X POST "%API_URL%/api/v1/tenants/setup" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"company_name\":\"测试公司\",\"clerk_user_id\":\"test_user_%random%\"}" > temp_tenant.json

findstr /C:"id" temp_tenant.json >nul
if %errorlevel% equ 0 (
    echo [OK] 租户创建成功
    type temp_tenant.json
) else (
    echo [WARN] 租户创建可能需要认证
)
del temp_tenant.json
echo.

REM 5. 测试数据源连接
echo [5/8] 测试数据源连接...
curl -s -X POST "%API_URL%/api/v1/data-sources/test" ^
  -H "Content-Type: application/json" ^
  -d "{\"connection_string\":\"postgresql://postgres:postgres@localhost:5432/data_agent\",\"db_type\":\"postgresql\"}" > temp_conn.json

findstr /C:"success" temp_conn.json >nul
if %errorlevel% equ 0 (
    echo [OK] 数据源连接测试通过
    type temp_conn.json
) else (
    echo [WARN] 数据源连接测试失败（可能是正常的）
)
del temp_conn.json
echo.

REM 6. 测试文档上传
echo [6/8] 测试文档上传...
echo This is a test PDF content > temp_test.pdf

curl -s -X POST "%API_URL%/api/v1/documents/upload" ^
  -F "file=@temp_test.pdf" > temp_upload.json

findstr /C:"id" temp_upload.json >nul
if %errorlevel% equ 0 (
    echo [OK] 文档上传成功
    type temp_upload.json
) else (
    echo [WARN] 文档上传可能需要认证
)
del temp_test.pdf
del temp_upload.json
echo.

REM 7. 测试LLM对话
echo [7/8] 测试LLM对话功能...
curl -s -X POST "%API_URL%/api/v1/llm/chat/completions" ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好，请用一句话介绍自己\"}],\"model\":\"glm-4-flash\"}" > temp_llm.json

findstr /C:"content" temp_llm.json >nul
if %errorlevel% equ 0 (
    echo [OK] LLM对话测试成功
    type temp_llm.json
) else (
    echo [WARN] LLM对话可能需要认证或API密钥
)
del temp_llm.json
echo.

REM 8. 测试前端访问
echo [8/8] 测试前端访问...
curl -s "%FRONTEND_URL%" > temp_frontend.html
findstr /C:"Data Agent V4" temp_frontend.html >nul
if %errorlevel% equ 0 (
    echo [OK] 前端服务正常
) else (
    echo [ERROR] 前端服务异常
)
del temp_frontend.html
echo.

REM 总结
echo ========================================
echo 测试完成！
echo ========================================
echo.
echo 可访问的前端页面：
echo   - 主页: %FRONTEND_URL%
echo   - 聊天界面: %FRONTEND_URL%/chat
echo   - 简化聊天: %FRONTEND_URL%/chat-simple
echo   - 数据源管理: %FRONTEND_URL%/data-sources
echo   - 文档管理: %FRONTEND_URL%/documents
echo.
echo 可访问的后端服务：
echo   - API文档: %API_URL%/docs
echo   - 健康检查: %API_URL%/health
echo   - MinIO控制台: http://localhost:9001 (minioadmin/minioadmin)
echo.
echo 提示：
echo   - 开发模式下，前端页面可直接访问，无需登录
echo   - 部分API可能需要认证，返回401是正常的
echo   - 详细测试指南请查看: docs/测试指南-功能测试手册.md
echo.

pause

