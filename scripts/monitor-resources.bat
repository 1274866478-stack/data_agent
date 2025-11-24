@echo off
echo ========================================
echo Data Agent V4 - Resource Monitor
echo ========================================
echo.

echo Checking Docker resource usage...
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"

echo.
echo System Resource Information:
systeminfo | find "Total Physical Memory"
systeminfo | find "Available Physical Memory"
systeminfo | find "Total Virtual Memory"
systeminfo | find "Available Virtual Memory"

echo.
echo Docker System Information:
docker system df

echo.
echo Container Health Status:
docker compose ps

echo.
echo ========================================
echo Resource Usage Tips:
echo ========================================
echo.
echo If you see high memory usage:
echo - Consider stopping unused containers: docker compose down
echo - Restart specific services: docker compose restart [service-name]
echo - Check for memory leaks in your applications
echo.
echo If you see high CPU usage:
echo - Check application logs for errors: docker compose logs [service-name]
echo - Monitor concurrent requests and database queries
echo - Consider scaling up your development machine
echo.
echo To continuously monitor resources:
echo docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo.
echo To clean up unused Docker resources:
echo docker system prune -a
echo.
pause