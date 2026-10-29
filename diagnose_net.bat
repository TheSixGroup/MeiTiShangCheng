@echo off
chcp 65001 >nul
cd /d %~dp0
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] venv not found: .venv
    pause
    exit /b 1
)
"%PY%" tools\diagnose_net.py
echo.
pause
