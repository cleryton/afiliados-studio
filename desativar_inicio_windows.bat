@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" background.py startup-off
) else (
    python background.py startup-off
)
if errorlevel 1 pause
