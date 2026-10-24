@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" background.py stop
) else (
    python background.py stop
)
if errorlevel 1 pause
