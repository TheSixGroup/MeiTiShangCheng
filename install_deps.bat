@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

set "PY=.venv\Scripts\python.exe"
if not defined PIP_TIMEOUT set "PIP_TIMEOUT=15"

if not exist "%PY%" (
    echo [ERROR] venv not found: .venv
    echo         Run: python -m venv .venv
    pause
    exit /b 1
)

"%PY%" -c "import flask, flask_restx, flask_sqlalchemy, flask_jwt_extended" >nul 2>&1
if not errorlevel 1 (
    echo [OK] dependencies already installed, nothing to do.
    pause
    exit /b 0
)

set "PIP=%PY% -m pip install -r requirements.txt --timeout %PIP_TIMEOUT% --retries 1 -q"
set "MIRROR_ARGS="

echo ============================================
echo  Installing backend dependencies
echo  (tries direct, then mirrors, then proxy)
echo ============================================

echo.
echo [1/6] direct  pypi.org ...
%PIP%
if not errorlevel 1 goto ok

echo [2/6] mirror  aliyun ...
%PIP% -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
if not errorlevel 1 goto ok

echo [3/6] mirror  tsinghua ...
%PIP% -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if not errorlevel 1 goto ok

echo [4/6] proxy   127.0.0.1:7890 ...
set "HTTP_PROXY=http://127.0.0.1:7890"
set "HTTPS_PROXY=http://127.0.0.1:7890"
%PIP%
if not errorlevel 1 goto ok

echo [5/6] proxy   127.0.0.1:7897 ...
set "HTTP_PROXY=http://127.0.0.1:7897"
set "HTTPS_PROXY=http://127.0.0.1:7897"
%PIP%
if not errorlevel 1 goto ok

echo [6/6] proxy   127.0.0.1:10809 ...
set "HTTP_PROXY=http://127.0.0.1:10809"
set "HTTPS_PROXY=http://127.0.0.1:10809"
%PIP%
if not errorlevel 1 goto ok

echo.
echo [FAIL] all attempts failed.
echo.
echo   Option A: connect to a phone hotspot, then run this file again.
echo   Option B: download wheels on a networked machine:
echo             python -m pip download -r requirements.txt -d wheels
echo             copy the "wheels" folder here, then run:
echo             "%PY%" -m pip install --no-index --find-links wheels -r requirements.txt
echo   Option C: start your VPN/proxy client, then run this file again.
echo.
pause
exit /b 1

:ok
echo.
echo [OK] dependencies installed successfully.
"%PY%" -c "import importlib.metadata as m; print('   flask           ', m.version('flask')); print('   flask-restx    ', m.version('flask-restx')); print('   flask-sqlalchemy', m.version('flask-sqlalchemy')); print('   flask-jwt-extended', m.version('flask-jwt-extended'))" 2>nul
echo.
echo Now double-click start.bat to launch the server.
pause
exit /b 0
