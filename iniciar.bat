@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" background.py start --open
) else (
    python background.py start --open
)
if errorlevel 1 pause
