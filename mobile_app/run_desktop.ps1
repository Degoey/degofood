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
# PENTING: JANGAN panggil ".\venv\Scripts\flet.exe".
# Launcher .exe buatan pip menyimpan path absolut venv saat dibuat
# (mis. "#!D:\FOODGO\mobile_app\venv\Scripts\python.exe"), sehingga
# rusak begitu folder repo di-rename. Paket flet tidak punya __main__,
# jadi dipanggil lewat modul flet.cli - tahan rename.
& ".\venv\Scripts\python.exe" -c "import sys; from flet.cli import main; sys.exit(main())" run main.py
