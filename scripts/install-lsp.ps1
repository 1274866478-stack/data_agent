# LSP Server Installation Script for Windows PowerShell
# Usage: .\scripts\install-lsp.ps1

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Data Agent V4 - LSP Setup Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Recommend running as administrator" -ForegroundColor Yellow
    Write-Host ""
}

# ==================== Python LSP ====================
Write-Host "[1/4] Installing Python LSP Server..." -ForegroundColor Green
Write-Host ""

Write-Host "  - Installing Pyright..." -ForegroundColor Cyan
try {
    npm install -g pyright
    Write-Host "    [OK] Pyright installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install Pyright" -ForegroundColor Red
}

Write-Host "  - Installing Python LSP Server..." -ForegroundColor Cyan
try {
    pip install python-lsp-server
    Write-Host "    [OK] python-lsp-server installed" -ForegroundColor Green
} catch {
    Write-Host "    [WARNING] Failed to install python-lsp-server" -ForegroundColor Yellow
}

Write-Host "  - Installing Black formatter..." -ForegroundColor Cyan
try {
    pip install black
    Write-Host "    [OK] Black installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install Black" -ForegroundColor Red
}

Write-Host "  - Installing isort..." -ForegroundColor Cyan
try {
    pip install isort
    Write-Host "    [OK] isort installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install isort" -ForegroundColor Red
}

Write-Host "  - Installing flake8..." -ForegroundColor Cyan
try {
    pip install flake8
    Write-Host "    [OK] flake8 installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install flake8" -ForegroundColor Red
}

Write-Host "  - Installing mypy..." -ForegroundColor Cyan
try {
    pip install mypy
    Write-Host "    [OK] mypy installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install mypy" -ForegroundColor Red
}

# ==================== TypeScript/JavaScript LSP ====================
Write-Host ""
Write-Host "[2/4] Installing TypeScript/JavaScript LSP Server..." -ForegroundColor Green
Write-Host ""

Write-Host "  - Installing TypeScript Language Server..." -ForegroundColor Cyan
try {
    npm install -g typescript-language-server
    Write-Host "    [OK] typescript-language-server installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install typescript-language-server" -ForegroundColor Red
}

Write-Host "  - Installing vtsls..." -ForegroundColor Cyan
try {
    npm install -g vtsls
    Write-Host "    [OK] vtsls installed" -ForegroundColor Green
} catch {
    Write-Host "    [WARNING] Failed to install vtsls" -ForegroundColor Yellow
}

Write-Host "  - Installing ESLint..." -ForegroundColor Cyan
try {
    npm install -g eslint
    Write-Host "    [OK] eslint installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install eslint" -ForegroundColor Red
}

Write-Host "  - Installing Prettier..." -ForegroundColor Cyan
try {
    npm install -g prettier
    Write-Host "    [OK] prettier installed" -ForegroundColor Green
} catch {
    Write-Host "    [ERROR] Failed to install prettier" -ForegroundColor Red
}

# ==================== Python Dependencies ====================
Write-Host ""
Write-Host "[3/4] Installing Python development dependencies..." -ForegroundColor Green
Write-Host ""

if (Test-Path "backend\requirements.txt") {
    Write-Host "  - Installing from requirements.txt..." -ForegroundColor Cyan
    try {
        if (Test-Path "backend\.venv\Scripts\python.exe") {
            & backend\.venv\Scripts\python.exe -m pip install --upgrade pip
            & backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
            Write-Host "    [OK] Python dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "    [WARNING] Python venv not found at backend\.venv" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    [ERROR] Failed to install Python dependencies" -ForegroundColor Red
    }
} else {
    Write-Host "  [WARNING] backend\requirements.txt not found" -ForegroundColor Yellow
}

# ==================== Frontend Dependencies ====================
Write-Host ""
Write-Host "[4/4] Installing frontend dependencies..." -ForegroundColor Green
Write-Host ""

if (Test-Path "frontend\package.json") {
    Write-Host "  - Installing from package.json..." -ForegroundColor Cyan
    try {
        Push-Location frontend
        npm install
        Pop-Location
        Write-Host "    [OK] Frontend dependencies installed" -ForegroundColor Green
    } catch {
        Write-Host "    [ERROR] Failed to install frontend dependencies" -ForegroundColor Red
    }
} else {
    Write-Host "  [WARNING] frontend\package.json not found" -ForegroundColor Yellow
}

# ==================== Completion ====================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Reload VS Code: Ctrl+Shift+P -> 'Reload Window'" -ForegroundColor White
Write-Host "2. Check Python: Ctrl+Shift+P -> 'Python: Select Interpreter'" -ForegroundColor White
Write-Host "3. Open a .py file to test Python IntelliSense" -ForegroundColor White
Write-Host "4. Open a .tsx file to test TypeScript IntelliSense" -ForegroundColor White
Write-Host ""
Write-Host "Troubleshooting:" -ForegroundColor Yellow
Write-Host "- Python path: backend\.venv\Scripts\python.exe" -ForegroundColor White
Write-Host "- Check Node.js: node --version (recommend >= 18)" -ForegroundColor White
Write-Host "- Check Python: python --version (recommend >= 3.8)" -ForegroundColor White
Write-Host ""
Write-Host "For VS Code extensions:" -ForegroundColor Cyan
Write-Host "  Press Ctrl+Shift+P -> 'Extensions: Show Recommended Extensions'" -ForegroundColor White
