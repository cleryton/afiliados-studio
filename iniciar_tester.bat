@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py --tester --open
) else (
    python app.py --tester --open
)
if errorlevel 1 pause
