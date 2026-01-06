@echo off
REM Agent测试运行脚本 - Windows版本

echo ========================================
echo   Data Agent V4 - Agent测试套件
echo ========================================
echo.

REM 设置工作目录
cd /d "%~dp0\..\Agent"

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [信息] 虚拟环境不存在，正在创建...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo [步骤 1/4] 检查依赖...
pip install -q pytest pytest-asyncio pytest-cov 2>nul
if %errorlevel% neq 0 (
    echo [警告] 安装测试依赖失败，尝试继续...
)

REM 解析命令行参数
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

echo.
echo ========================================
echo   运行测试: %TEST_TYPE%
echo ========================================
echo.

REM 根据参数运行不同的测试
if "%TEST_TYPE%"=="unit" (
    echo [步骤 2/4] 运行单元测试...
    pytest tests/unit -v --cov --cov-report=term-missing
    goto :check_result
)

if "%TEST_TYPE%"=="integration" (
    echo [步骤 2/4] 运行集成测试...
    pytest tests/integration -v -m integration
    goto :check_result
)

if "%TEST_TYPE%"=="e2e" (
    echo [步骤 2/4] 运行端到端测试...
    pytest tests/e2e -v -m e2e
    goto :check_result
)

if "%TEST_TYPE%"=="golden" (
    echo [步骤 2/4] 运行黄金测试用例...
    pytest tests/unit/test_golden_cases.py -v
    goto :check_result
)

if "%TEST_TYPE%"=="quick" (
    echo [步骤 2/4] 运行快速测试（仅单元测试）...
    pytest tests/unit -v --tb=short
    goto :check_result
)

if "%TEST_TYPE%"=="all" (
    echo [步骤 2/4] 运行所有测试...
    pytest tests/ -v --cov --cov-report=html --cov-report=term
    goto :check_result
)

REM 未知的测试类型
echo [错误] 未知的测试类型: %TEST_TYPE%
echo.
echo 支持的测试类型:
echo   all         - 运行所有测试（默认）
echo   unit        - 仅运行单元测试
echo   integration - 仅运行集成测试
echo   e2e         - 仅运行端到端测试
echo   golden      - 仅运行黄金测试用例
echo   quick       - 快速测试（单元测试，简化输出）
echo.
echo 使用示例:
echo   run_agent_tests.bat
echo   run_agent_tests.bat unit
echo   run_agent_tests.bat golden
pause
exit /b 1

:check_result
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   ✓ 测试通过
    echo ========================================

    REM 如果运行了覆盖率测试，显示报告位置
    if exist "htmlcov\index.html" (
        echo.
        echo [信息] HTML覆盖率报告已生成: htmlcov\index.html
        echo 可以在浏览器中打开查看详细报告
    )

    echo.
) else (
    echo.
    echo ========================================
    echo   ✗ 测试失败
    echo ========================================
    echo.
    echo [建议] 查看上方的错误信息修复问题
    echo [建议] 运行 'pytest tests/ -v -x' 在第一个失败处停止
    echo.
)

REM 保持窗口打开
if "%2"=="--no-pause" goto :eof
pause
