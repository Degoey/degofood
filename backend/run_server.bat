@echo off
setlocal
cd /d "%~dp0"
REM Catatan: pakai `python.exe -m uvicorn`, BUKAN `uvicorn.exe`.
REM Launcher .exe menyimpan path absolut saat dibuat, sehingga rusak
REM bila folder repo di-rename / dipindah.
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
