@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute instalar.bat antes de validar o projeto.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\validate.py --report artifacts\validation-report.json
set "validationResult=%errorlevel%"
echo.
echo As verificacoes de seguranca adicionais aparecem na aba Actions do GitHub.
pause
exit /b %validationResult%
