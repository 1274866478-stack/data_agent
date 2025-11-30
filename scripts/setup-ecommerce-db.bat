@echo off
REM ================================================================
REM 电商测试数据库快速初始化脚本 (Windows)
REM ================================================================

echo ========================================
echo 电商测试数据库初始化工具
echo ========================================
echo.

REM 设置数据库连接参数
set PGHOST=localhost
set PGPORT=5432
set PGUSER=dev
set PGPASSWORD=dev123
set PGDATABASE=postgres
set NEW_DB=ecommerce_test_db

echo [1/4] 检查PostgreSQL连接...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c "SELECT version();" >nul 2>&1
if errorlevel 1 (
    echo ❌ 无法连接到PostgreSQL，请检查：
    echo    - PostgreSQL服务是否运行
    echo    - 连接参数是否正确 ^(主机: %PGHOST%, 端口: %PGPORT%, 用户: %PGUSER%^)
    pause
    exit /b 1
)
echo ✅ PostgreSQL连接成功

echo.
echo [2/4] 检查数据库是否存在...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -tAc "SELECT 1 FROM pg_database WHERE datname='%NEW_DB%'" | findstr "1" >nul
if not errorlevel 1 (
    echo ⚠️  数据库 %NEW_DB% 已存在
    set /p CONFIRM="是否删除并重新创建? (y/N): "
    if /i not "%CONFIRM%"=="y" (
        echo 取消操作
        pause
        exit /b 0
    )
    echo 正在删除旧数据库...
    psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c "DROP DATABASE IF EXISTS %NEW_DB%;"
)

echo.
echo [3/4] 创建新数据库...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c "CREATE DATABASE %NEW_DB%;"
if errorlevel 1 (
    echo ❌ 创建数据库失败
    pause
    exit /b 1
)
echo ✅ 数据库创建成功

echo.
echo [4/4] 初始化数据...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %NEW_DB% -f init-ecommerce-test-db.sql
if errorlevel 1 (
    echo ❌ 数据初始化失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 电商测试数据库初始化完成！
echo ========================================
echo.
echo 数据库信息:
echo   - 数据库名: %NEW_DB%
echo   - 主机: %PGHOST%
echo   - 端口: %PGPORT%
echo   - 用户: %PGUSER%
echo.
echo 连接字符串:
echo   postgresql://%PGUSER%:%PGPASSWORD%@%PGHOST%:%PGPORT%/%NEW_DB%
echo.
echo 数据统计:
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %NEW_DB% -c "SELECT (SELECT COUNT(*) FROM users) as users, (SELECT COUNT(*) FROM products) as products, (SELECT COUNT(*) FROM orders) as orders, (SELECT COUNT(*) FROM reviews) as reviews;"
echo.
echo 下一步:
echo   1. 在Data Agent中添加此数据源
echo   2. 使用AI助手测试数据查询
echo   3. 查看 电商测试数据库使用指南.md 了解更多示例
echo.
pause

