@echo off
REM Frontend 清理脚本 (Windows版本)
REM 清理不必要的文件，保持项目结构整洁

echo 🧹 开始清理前端项目...

REM 清理构建缓存
echo 清理构建缓存...
if exist ".next" rmdir /s /q ".next"
if exist "node_modules\.cache" rmdir /s /q "node_modules\.cache"

REM 清理测试覆盖率报告
echo 清理测试覆盖率报告...
if exist "coverage" rmdir /s /q "coverage"

REM 清理TypeScript构建输出
echo 清理TypeScript输出...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM 清理日志文件
echo 清理日志文件...
for /r %%i in (*.log) do del "%%i"

REM 清理临时文件
echo 清理临时文件...
for /r %%i in (.DS_Store) do del "%%i"
for /r %%i in (Thumbs.db) do del "%%i"

echo ✅ 清理完成！
echo.
echo 💡 提示：如果需要重新安装依赖，请运行：
echo    npm install
echo.
echo 💡 提示：如果需要重新构建，请运行：
echo    npm run build

pause