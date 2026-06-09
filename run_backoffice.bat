@echo off
setlocal

cd /d "%~dp0"
title FortGuard Server

set "APP_URL=http://localhost:8501"
set "HEALTH_URL=http://127.0.0.1:8501/_stcore/health"
set "PYTHON_EXE="

if exist "tools\python313\python.exe" set "PYTHON_EXE=tools\python313\python.exe"
if not defined PYTHON_EXE if exist ".venv-backoffice\Scripts\python.exe" set "PYTHON_EXE=.venv-backoffice\Scripts\python.exe"
if not defined PYTHON_EXE if exist "venv\Scripts\python.exe" set "PYTHON_EXE=venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    echo Nao encontrei o Python do FortGuard.
    echo Verifique se a pasta tools\python313 existe dentro desta pasta.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($r.Content -eq 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }"
if %ERRORLEVEL% EQU 0 (
    echo FortGuard ja esta rodando.
    echo Abrindo o sistema no navegador...
    start "" "%APP_URL%"
    exit /b 0
)

echo ================================================
echo  FORTGUARD - SISTEMA LOCAL
echo ================================================
echo.
echo O sistema vai abrir no navegador em alguns segundos.
echo.
echo IMPORTANTE:
echo Mantenha esta janela aberta enquanto estiver usando.
echo Para encerrar o sistema, feche esta janela.
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 7; Start-Process '%APP_URL%'"

"%PYTHON_EXE%" -m streamlit run backoffice_streamlit.py --server.address 127.0.0.1 --server.port 8501 --server.headless true

echo.
echo O FortGuard foi encerrado.
echo Se isso aconteceu sem voce querer, tire uma foto desta tela para vermos o erro.
pause
