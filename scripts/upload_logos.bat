@echo off
REM DataAgent V4.1 Logo上传脚本
REM 用于上传logo资源到MinIO存储

echo ================================
echo DataAgent V4.1 Logo资源上传工具
echo ================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境
    echo 请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "backend\venv" (
    echo ❌ 错误: 未找到Python虚拟环境
    echo 请先运行 setup_dev.bat 创建虚拟环境
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call backend\venv\Scripts\activate.bat

REM 切换到脚本目录
cd /d "%~dp0"

REM 检查logo文件是否存在
if not exist "..\docs\design\logo\DataAgent_V4_1_Logo_Enhanced.svg" (
    echo ❌ 错误: Logo文件不存在
    echo 请确保logo文件已生成: docs\design\logo\DataAgent_V4_1_Logo_Enhanced.svg
    pause
    exit /b 1
)

echo ✅ Logo文件检查通过
echo.

REM 显示当前配置
echo 📋 当前配置信息:
echo   - 项目目录: %CD%\..
echo   - Logo文件: ..\docs\design\logo\DataAgent_V4_1_Logo_Enhanced.svg
echo   - 上传脚本: upload_assets.py
echo.

REM 询问用户是否继续
set /p confirm="🚀 确认开始上传Logo资源到MinIO? (y/N): "
if /i not "%confirm%"=="y" if /i not "%confirm%"=="yes" (
    echo ❌ 用户取消操作
    pause
    exit /b 0
)

echo.
echo ⬆️ 开始上传Logo资源...
echo =================================

REM 执行上传脚本
python upload_assets.py --type logos

REM 检查执行结果
if errorlevel 1 (
    echo.
    echo ❌ Logo上传失败
    echo 请检查:
    echo   1. MinIO服务是否正在运行
    echo   2. 环境变量配置是否正确 (.env文件)
    echo   3. 网络连接是否正常
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Logo上传成功完成！
    echo.
    echo 📋 接下来可以:
    echo   1. 访问MinIO控制台: http://localhost:9001
    echo   2. 查看上传的logo文件
    echo   3. 在前端应用中使用新的logo
    echo.
)

pause