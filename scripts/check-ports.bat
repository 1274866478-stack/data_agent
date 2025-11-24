@echo off
echo ========================================
echo Data Agent V4 - Port Conflict Checker
echo ========================================
echo.

set PORTS[0]=3000 Frontend
set PORTS[1]=8004 Backend
set PORTS[2]=5432 PostgreSQL
set PORTS[3]=9000 MinIO-API
set PORTS[4]=9001 MinIO-Console
set PORTS[5]=8001 ChromaDB

set CONFLICTS=0

echo Scanning for port conflicts...
echo.

for %%P in (3000 8004 5432 9000 9001 8001) do (
    echo Checking port %%P...
    netstat -ano | find ":%%P " > nul
    if !ERRORLEVEL! EQU 0 (
        echo [CONFLICT] Port %%P is in use:
        netstat -ano | find ":%%P "
        echo.

        REM Find the process using the port
        for /f "tokens=5" %%A in ('netstat -ano ^| find ":%%P "') do (
            echo Process ID: %%A
            tasklist /fi "PID eq %%A" /fo table /nh
        )
        echo ------------------------------------------------
        set /a CONFLICTS+=1
    ) else (
        echo [FREE] Port %%P is available
    )
    echo.
)

echo ========================================
echo Port Scan Summary:
echo ========================================
if %CONFLICTS% GTR 0 (
    echo Found %CONFLICTS% port conflict^(s^)
    echo.
    echo Resolution Options:
    echo 1. Stop the conflicting application^(s^) manually
    echo 2. Change the port mapping in docker-compose.yml
    echo 3. Use a different development environment
    echo.
    echo To find processes using ports:
    echo netstat -ano ^| find ":PORT_NUMBER"
    echo taskkill /PID PROCESS_ID /F
) else (
    echo All required ports are available!
    echo Ready to start Data Agent services.
)
echo.
pause