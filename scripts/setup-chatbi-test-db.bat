@echo off
REM ================================================================
REM ChatBI 测试数据库设置脚本
REM 用户: dev@dataagent.local
REM ================================================================

echo.
echo ========================================
echo   ChatBI 测试数据库设置工具
echo ========================================
echo.

REM 数据库配置 - 请根据实际情况修改
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=chatbi_test
set DB_USER=postgres
set DB_PASSWORD=postgres

echo 数据库配置:
echo   主机: %DB_HOST%
echo   端口: %DB_PORT%
echo   数据库名: %DB_NAME%
echo   用户: %DB_USER%
echo.

REM 检查 psql 命令是否可用
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 psql 命令。请确保 PostgreSQL 已安装并添加到 PATH。
    echo.
    echo 可选方案:
    echo   1. 安装 PostgreSQL 并将 bin 目录添加到 PATH
    echo   2. 使用 Docker: docker exec -i postgres psql ...
    pause
    exit /b 1
)

echo [1/3] 创建数据库 %DB_NAME% (如果不存在)...
set PGPASSWORD=%DB_PASSWORD%
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d postgres -c "CREATE DATABASE %DB_NAME%;" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       数据库创建成功!
) else (
    echo       数据库已存在，跳过创建。
)

echo.
echo [2/3] 执行初始化脚本...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "%~dp0init-chatbi-test-db.sql"
if %ERRORLEVEL% NEQ 0 (
    echo [错误] SQL 脚本执行失败!
    pause
    exit /b 1
)

echo.
echo [3/3] 验证数据...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT 'regions' as table_name, COUNT(*) as count FROM regions UNION ALL SELECT 'employees', COUNT(*) FROM employees UNION ALL SELECT 'categories', COUNT(*) FROM categories UNION ALL SELECT 'products', COUNT(*) FROM products UNION ALL SELECT 'customers', COUNT(*) FROM customers UNION ALL SELECT 'orders', COUNT(*) FROM orders UNION ALL SELECT 'order_items', COUNT(*) FROM order_items;"

echo.
echo ========================================
echo   测试数据库设置完成!
echo ========================================
echo.
echo 连接字符串:
echo   postgresql://%DB_USER%:%DB_PASSWORD%@%DB_HOST%:%DB_PORT%/%DB_NAME%
echo.
echo 可以在 Data Agent 中使用以下连接信息:
echo   Host: %DB_HOST%
echo   Port: %DB_PORT%
echo   Database: %DB_NAME%
echo   User: %DB_USER%
echo   Password: %DB_PASSWORD%
echo.
echo 示例 ChatBI 查询:
echo   - 今年销售额最高的产品是什么？
echo   - 哪个销售员的业绩最好？
echo   - 上个月有多少订单？
echo   - VIP客户的订单总额是多少？
echo.
pause

