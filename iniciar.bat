@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launcher.py --open
) else (
    python launcher.py --open
)
if errorlevel 1 pause
