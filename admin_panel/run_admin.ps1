# Run DEGOFOOD admin panel (FastAPI web UI)
# Sesuaikan BACKEND_URL dengan URL backend yang sedang berjalan.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$env:BACKEND_URL = 'http://127.0.0.1:8000'
$env:ADMIN_USERNAME = 'admin'
$env:ADMIN_PASSWORD = 'admin123'
$env:ADMIN_API_KEY = ''          # isi jika backend membutuhkan X-Admin-Key
$env:SESSION_SECRET = 'rahasia-session'

# Catatan: gunakan `python -m uvicorn`, BUKAN `uvicorn.exe`.
# Launcher `uvicorn.exe` menyimpan path absolut saat dibuat sehingga rusak
# bila folder repo di-rename / dipindah. `python.exe` tetap valid.
if (Test-Path .\venv\Scripts\python.exe) {
    .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
} else {
    python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
}
