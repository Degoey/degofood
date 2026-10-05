# Run DEGOFOOD backend with auto-reload on all interfaces (port 8000)
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
if (Test-Path .\venv\Scripts\uvicorn.exe) {
    .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
