@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_pythonanywhere_package.ps1"
pause
