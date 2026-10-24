@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" background.py startup-on
) else (
    python background.py startup-on
)
if errorlevel 1 pause
