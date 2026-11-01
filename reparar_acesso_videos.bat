@echo off
setlocal
cd /d "%~dp0"
echo Este reparador autoriza somente data\stories no navegador do projeto.
echo Nao envia arquivos nem altera permissoes do Windows.
if not exist ".venv\Scripts\python.exe" (
  echo Abra iniciar.bat primeiro para preparar o aplicativo.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\configure_browser_access.py --apply
pause
