# 端口冲突检测脚本 (Windows PowerShell)
# 检查Data Agent V4所需的端口是否被占用

# 需要检查的端口
$ports = @{
    3000 = "Frontend (Next.js)"
    8004 = "Backend (FastAPI)"
    5432 = "PostgreSQL"
    9000 = "MinIO API"
    9001 = "MinIO Console"
    8001 = "ChromaDB"
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Data Agent V4 - 端口冲突检测" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$conflicts = 0

foreach ($port in $ports.Keys | Sort-Object) {
    $service = $ports[$port]
    
    # 检查端口是否被占用
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    
    if ($connection) {
        Write-Host "✗ 端口 " -NoNewline -ForegroundColor Red
        Write-Host "$port " -NoNewline -ForegroundColor Yellow
        Write-Host "已被占用 - $service" -ForegroundColor White
        
        # 显示占用端口的进程信息
        $processId = $connection.OwningProcess | Select-Object -First 1
        if ($processId) {
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  占用进程: PID $processId ($($process.ProcessName))" -ForegroundColor Gray
            }
        }
        
        $conflicts++
    } else {
        Write-Host "✓ 端口 " -NoNewline -ForegroundColor Green
        Write-Host "$port " -NoNewline -ForegroundColor Yellow
        Write-Host "可用 - $service" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

if ($conflicts -eq 0) {
    Write-Host "✓ 所有端口可用，可以启动Docker环境" -ForegroundColor Green
    Write-Host ""
    Write-Host "运行以下命令启动服务:" -ForegroundColor White
    Write-Host "  docker-compose up -d" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "✗ 发现 $conflicts 个端口冲突" -ForegroundColor Red
    Write-Host ""
    Write-Host "解决方案:" -ForegroundColor Yellow
    Write-Host "1. 停止占用端口的进程" -ForegroundColor White
    Write-Host "2. 修改 docker-compose.yml 中的端口映射" -ForegroundColor White
    Write-Host "3. 使用 docker-compose.override.yml 自定义端口" -ForegroundColor White
    Write-Host ""
    Write-Host "示例 - 停止占用端口的进程:" -ForegroundColor Yellow
    Write-Host "  Stop-Process -Id <PID>" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "示例 - 创建 docker-compose.override.yml:" -ForegroundColor Yellow
    Write-Host "  services:" -ForegroundColor Cyan
    Write-Host "    frontend:" -ForegroundColor Cyan
    Write-Host "      ports:" -ForegroundColor Cyan
    Write-Host "        - `"3001:3000`"  # 使用3001代替3000" -ForegroundColor Cyan
    exit 1
}

