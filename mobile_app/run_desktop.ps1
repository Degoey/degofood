# Jalankan aplikasi DEGOFOOD Mobile di desktop untuk development
# Contoh: .\run_desktop.ps1 -ApiUrl "http://127.0.0.1:8000"
param(
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

$env:PYTHONIOENCODING = "utf-8"

# Update API_BASE_URL di main.py sesuai parameter
$mainPath = Join-Path $scriptDir "main.py"
$mainContent = Get-Content $mainPath -Raw
$mainContent = $mainContent -replace "API_BASE_URL = .*", "API_BASE_URL = '$ApiUrl'"
Set-Content -Path $mainPath -Value $mainContent -NoNewline

Write-Host "Menjalankan DEGOFOOD Mobile dengan API_BASE_URL = $ApiUrl" -ForegroundColor Green
& ".\venv\Scripts\flet.exe" "run" "main.py"
