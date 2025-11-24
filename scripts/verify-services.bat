@echo off
echo ========================================
echo Data Agent V4 - Services Verification
echo ========================================
echo.

echo Checking Docker Compose configuration...
docker compose config --quiet
if %ERRORLEVEL% EQU 0 (
    echo [✓] Docker Compose configuration is valid
) else (
    echo [✗] Docker Compose configuration has errors
    exit /b 1
)
echo.

echo Checking required files...
if not exist ".env" (
    echo [✗] .env file not found
    exit /b 1
) else (
    echo [✓] .env file exists
)

if not exist "docker-compose.yml" (
    echo [✗] docker-compose.yml not found
    exit /b 1
) else (
    echo [✓] docker-compose.yml exists
)

if not exist "frontend\Dockerfile" (
    echo [✗] Frontend Dockerfile not found
    exit /b 1
) else (
    echo [✓] Frontend Dockerfile exists
)

if not exist "backend\Dockerfile" (
    echo [✗] Backend Dockerfile not found
    exit /b 1
) else (
    echo [✓] Backend Dockerfile exists
)

if not exist "backend\scripts\init-db.sql" (
    echo [✗] Database init script not found
    exit /b 1
) else (
    echo [✓] Database init script exists
)
echo.

echo Checking port availability...
netstat -an | find "3000" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 3000 may be in use (Frontend)
) else (
    echo [✓] Port 3000 is available (Frontend)
)

netstat -an | find "8004" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 8004 may be in use (Backend)
) else (
    echo [✓] Port 8004 is available (Backend)
)

netstat -an | find "5432" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 5432 may be in use (Database)
) else (
    echo [✓] Port 5432 is available (Database)
)

netstat -an | find "9000" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 9000 may be in use (MinIO)
) else (
    echo [✓] Port 9000 is available (MinIO)
)

netstat -an | find "8001" > nul
if %ERRORLEVEL% EQU 0 (
    echo [⚠] Port 8001 may be in use (ChromaDB)
) else (
    echo [✓] Port 8001 is available (ChromaDB)
)
echo.

echo ========================================
echo Verification Summary:
echo All configuration files are present and valid
echo Port status has been checked
echo Ready to start services with: docker compose up --build
echo ========================================
pause