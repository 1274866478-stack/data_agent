@echo off
echo ========================================
echo Data Agent V4 - Services Startup
echo ========================================
echo.

echo Checking Docker availability...
docker --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [✗] Docker is not installed or not running
    echo Please install Docker Desktop and ensure it's running
    pause
    exit /b 1
)

echo [✓] Docker is available
echo.

echo Checking port availability...
call scripts\verify-services.bat > nul 2>&1

echo Checking for port conflicts...
netstat -an | find ":3000" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 3000 is already in use
    echo    This will prevent the Frontend service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

netstat -an | find ":8004" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 8004 is already in use
    echo    This will prevent the Backend service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

netstat -an | find ":5432" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 5432 is already in use
    echo    This will prevent the Database service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

netstat -an | find ":9000" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 9000 is already in use
    echo    This will prevent the MinIO API service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

netstat -an | find ":9001" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 9001 is already in use
    echo    This will prevent the MinIO Console service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

netstat -an | find ":8001" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 8001 is already in use
    echo    This will prevent the ChromaDB service from starting
    choice /M "Do you want to continue anyway"
    if %ERRORLEVEL% NEQ 1 (
        echo Startup cancelled by user
        pause
        exit /b 1
    )
)

echo [✓] Port check completed
echo.

echo Stopping any existing services...
docker compose down -v
echo.

echo Building and starting all services...
echo This may take several minutes on first run...
echo.

docker compose up --build -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [✓] Services started successfully!
    echo.
    echo Service URLs:
    echo - Frontend: http://localhost:3000
    echo - Backend: http://localhost:8004
    echo - Backend Docs: http://localhost:8004/docs
    echo - MinIO Console: http://localhost:9001
    echo - MinIO API: http://localhost:9000
    echo - ChromaDB: http://localhost:8001
    echo.
    echo Checking service health...
    timeout /t 30 /nobreak > nul

    echo Checking service status...
    docker compose ps

    echo.
    echo Useful Commands:
    echo - View logs: docker compose logs -f
    echo - Stop services: docker compose down
    echo - Verify services: scripts\verify-services.bat
    echo - Check ports: scripts\check-ports.bat
    echo - Monitor resources: scripts\monitor-resources.bat
    echo - Production security: docs\production-security-guide.md
) else (
    echo [✗] Failed to start services
    echo Check the error messages above
    echo You can view logs with: docker compose logs
)

echo.
pause