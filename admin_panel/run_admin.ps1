# Run DEGOFOOD admin panel (FastAPI web UI)
# Sesuaikan BACKEND_URL dengan URL backend yang sedang berjalan.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$env:BACKEND_URL = 'http://127.0.0.1:8000'
$env:ADMIN_USERNAME = 'admin'
$env:ADMIN_PASSWORD = 'admin123'
$env:ADMIN_API_KEY = ''          # isi jika backend membutuhkan X-Admin-Key
$env:SESSION_SECRET = 'rahasia-session'

if (Test-Path .\venv\Scripts\uvicorn.exe) {
    .\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8001 --reload
} else {
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload
}
