# Run DEGOFOOD backend with auto-reload on all interfaces (default port 8000).
# Ubah port bila 8000 sudah dipakai:  $env:DEGOFOOD_PORT = '8020'
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

$port = if ($env:DEGOFOOD_PORT) { $env:DEGOFOOD_PORT } else { '8000' }

# Catatan: gunakan `python -m uvicorn`, BUKAN `uvicorn.exe`.
# Launcher `uvicorn.exe` menyimpan path absolut saat dibuat sehingga rusak
# bila folder repo di-rename / dipindah. `python.exe` tetap valid.
if (Test-Path .\venv\Scripts\python.exe) {
    .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $port --reload
} else {
    python -m uvicorn app.main:app --host 0.0.0.0 --port $port --reload
}
