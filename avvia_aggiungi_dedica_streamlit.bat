@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\streamlit.exe" (
  ".venv\Scripts\streamlit.exe" run "scripts\aggiungi_dedica_streamlit.py"
  goto end
)

where streamlit >nul 2>nul
if %errorlevel%==0 (
  streamlit run "scripts\aggiungi_dedica_streamlit.py"
  goto end
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m streamlit run "scripts\aggiungi_dedica_streamlit.py"
  goto end
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m streamlit run "scripts\aggiungi_dedica_streamlit.py"
  goto end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -m streamlit run "scripts\aggiungi_dedica_streamlit.py"
  goto end
)

echo Streamlit o Python non trovato.
echo Installa le dipendenze con: pip install -r requirements.txt

:end
pause
