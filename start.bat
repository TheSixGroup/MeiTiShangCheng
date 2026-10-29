@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ERROR] venv not found: .venv
    echo         Run: python -m venv .venv
    pause
    exit /b 1
)

"%PY%" -c "import flask, flask_restx, flask_sqlalchemy, flask_jwt_extended" 2>nul
if errorlevel 1 (
    echo [ERROR] dependencies not installed
    echo         Run: "%PY%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist backend\data.db (
    echo [INFO] backend\data.db not found, seeding...
    "%PY%" backend\seed.py
    if errorlevel 1 (
        echo [ERROR] seeding failed
        pause
        exit /b 1
    )
)

echo ========================================
echo  Meiti Shangcheng - Backend Server
echo  BaseURL    : http://localhost:5000/api/v1
echo  Swagger UI : http://localhost:5000/api/docs
echo  Health     : http://localhost:5000/api/v1/health
echo ========================================

"%PY%" backend\app.py
echo.
echo [INFO] server exited with code %ERRORLEVEL%
pause
