# Run DEGOFOOD backend with auto-reload on all interfaces (port 8000)
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
# Catatan: gunakan `python -m uvicorn`, BUKAN `uvicorn.exe`.
# Launcher `uvicorn.exe` menyimpan path absolut saat dibuat sehingga rusak
# bila folder repo di-rename / dipindah. `python.exe` tetap valid.
if (Test-Path .\venv\Scripts\python.exe) {
    .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
