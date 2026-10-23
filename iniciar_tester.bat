@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launcher.py --tester --open
) else (
    python launcher.py --tester --open
)
if errorlevel 1 pause
