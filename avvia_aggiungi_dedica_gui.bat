@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\aggiungi_dedica_gui.py"
  goto end
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "scripts\aggiungi_dedica_gui.py"
  goto end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "scripts\aggiungi_dedica_gui.py"
  goto end
)

echo Python non trovato. Installa Python o crea una virtualenv in .venv.

:end
pause
