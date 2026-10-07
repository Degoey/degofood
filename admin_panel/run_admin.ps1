# Run DEGOFOOD admin panel (FastAPI web UI)
# Port default 8001 -> ubah dengan:  $env:DEGOFOOD_ADMIN_PORT = '8021'
# BACKEND_URL default http://127.0.0.1:8000 -> set lebih dulu bila backend di port lain.
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$port = if ($env:DEGOFOOD_ADMIN_PORT) { $env:DEGOFOOD_ADMIN_PORT } else { '8001' }

if (-not $env:BACKEND_URL)   { $env:BACKEND_URL   = 'http://127.0.0.1:8000' }
if (-not $env:ADMIN_USERNAME) { $env:ADMIN_USERNAME = 'admin' }
if (-not $env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD = 'admin123' }
if (-not $env:ADMIN_API_KEY)  { $env:ADMIN_API_KEY  = '' }   # isi jika backend butuh X-Admin-Key
if (-not $env:SESSION_SECRET) { $env:SESSION_SECRET = 'rahasia-session' }

# Catatan: gunakan `python -m uvicorn`, BUKAN `uvicorn.exe`.
# Launcher `uvicorn.exe` menyimpan path absolut saat dibuat sehingga rusak
# bila folder repo di-rename / dipindah. `python.exe` tetap valid.
if (Test-Path .\venv\Scripts\python.exe) {
    .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port $port --reload
} else {
    python -m uvicorn main:app --host 0.0.0.0 --port $port --reload
}
