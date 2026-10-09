# scripts/start_dev.ps1 — Lanceur Dev Backend FastAPI + Frontend Vite
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   AGIseed Ecosystem — Démarrage Dev Backend & Frontend  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Détection du binaire Python 3.13 opérationnel
$PYTHON_BIN = ""
try {
    $test = py -3.13 -c "import uvicorn; print('ok')" 2>$null
    if ($test -eq "ok") {
        $PYTHON_BIN = "py -3.13"
    }
} catch {}

if (-not $PYTHON_BIN) {
    $altPath = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    if (Test-Path $altPath) {
        $PYTHON_BIN = "& `"$altPath`""
    }
}

if (-not $PYTHON_BIN) {
    Write-Host "[ERREUR] Impossible de trouver Python 3.13 avec uvicorn." -ForegroundColor Red
    Write-Host "Installez les dépendances via: py -3.13 -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Interpréteur Python détecté: $PYTHON_BIN" -ForegroundColor Green

# 2. Lancement du Backend FastAPI dans un terminal séparé
Write-Host "[...] Démarrage du Backend FastAPI sur http://localhost:8000" -ForegroundColor Yellow
$backendCmd = "cd `"$PSScriptRoot\..`"; $PYTHON_BIN -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 3. Lancement du Frontend Vite
Write-Host "[...] Démarrage du Frontend Vite sur http://localhost:5173" -ForegroundColor Yellow
Set-Location "$PSScriptRoot\..\frontend"
npm run dev
