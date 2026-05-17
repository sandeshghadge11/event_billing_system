param(
  [switch]$SkipPythonVenv,
  [switch]$SkipNpmInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$EnvFile = Join-Path $Backend ".env"
$EnvExample = Join-Path $Backend ".env.example"

Write-Host "Preparing Prasad FX Billing for Windows..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found. Run scripts\install-windows.bat, or install Python 3.12+ and tick 'Add python.exe to PATH'."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm was not found. Run scripts\install-windows.bat, or install Node.js LTS."
}

if (-not (Test-Path $EnvFile)) {
  Copy-Item $EnvExample $EnvFile
  Write-Host "Created backend\.env from backend\.env.example" -ForegroundColor Yellow
  Write-Host "Edit backend\.env and set DATABASE_URL before using the app." -ForegroundColor Yellow
}

if (-not $SkipPythonVenv) {
  Push-Location $Backend
  if (-not (Test-Path ".venv")) {
    python -m venv .venv
  }
  .\.venv\Scripts\python -m pip install --upgrade pip
  .\.venv\Scripts\python -m pip install -r requirements.txt
  Pop-Location
}

if (-not $SkipNpmInstall) {
  Push-Location $Frontend
  npm install
  Pop-Location

  Push-Location $Root
  npm install
  Pop-Location
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Confirm MySQL is running and the database/user in backend\.env exists."
Write-Host "2. Run: .\scripts\run-windows-desktop.ps1"
