@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 bootstrap.py
) else (
    python bootstrap.py
)
if errorlevel 1 (
    echo Falha na instalacao. Consulte docs\MANUAL_TESTER.md.
    pause
    exit /b 1
)
pause
