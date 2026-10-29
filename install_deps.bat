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

"%PY%" -c "import flask, flask_restx, flask_sqlalchemy, flask_jwt_extended" >nul 2>&1
if not errorlevel 1 (
    echo [OK] dependencies already installed, nothing to do.
    pause
    exit /b 0
)

echo ============================================
echo  Installing backend dependencies
echo  Each route is probed with curl (6s) first,
echo  unreachable routes are skipped immediately.
echo ============================================

call :attempt "1/6 direct  pypi.org" "https://pypi.org/simple/" ""
if not errorlevel 1 goto ok

call :attempt "2/6 mirror  aliyun" "https://mirrors.aliyun.com/pypi/simple/" ""
if not errorlevel 1 goto ok

call :attempt "3/6 mirror  tsinghua" "https://pypi.tuna.tsinghua.edu.cn/simple" ""
if not errorlevel 1 goto ok

call :attempt "4/6 proxy   127.0.0.1:7890" "https://pypi.org/simple/" "http://127.0.0.1:7890"
if not errorlevel 1 goto ok

call :attempt "5/6 proxy   127.0.0.1:7897" "https://pypi.org/simple/" "http://127.0.0.1:7897"
if not errorlevel 1 goto ok

call :attempt "6/6 proxy   127.0.0.1:10809" "https://pypi.org/simple/" "http://127.0.0.1:10809"
if not errorlevel 1 goto ok

echo.
echo [FAIL] no route can reach PyPI.
echo.
echo   Option A: turn on your VPN/proxy client, then run this file again.
echo             (if your proxy port is not 7890 / 7897 / 10809, edit the call lines above)
echo   Option B: connect to a phone hotspot, then run this file again.
echo   Option C: offline install on a networked machine:
echo             python -m pip download -r requirements.txt -d wheels --only-binary=:all:
echo             copy the "wheels" folder here, then run:
echo             "%PY%" -m pip install --no-index --find-links wheels -r requirements.txt
echo.
pause
exit /b 1

:attempt
set "LABEL=%~1"
set "INDEX=%~2"
set "PROXY=%~3"
echo.
echo [%LABEL%] ...
set "HTTP_PROXY=%PROXY%"
set "HTTPS_PROXY=%PROXY%"
set "http_proxy=%PROXY%"
set "https_proxy=%PROXY%"
set "CURLARG="
if defined PROXY set "CURLARG=--proxy %PROXY%"
curl -s -o NUL --fail --max-time 6 %CURLARG% "%INDEX%" >nul 2>&1
if errorlevel 1 (
    echo       unreachable, skipped.
    exit /b 1
)
echo       reachable, installing (may take 1-2 minutes) ...
"%PY%" -m pip install -r requirements.txt --timeout 15 --retries 1 -q -i "%INDEX%"
exit /b %errorlevel%

:ok
echo.
echo [OK] dependencies installed successfully.
"%PY%" -c "import importlib.metadata as m; print('   flask             ', m.version('flask')); print('   flask-restx      ', m.version('flask-restx')); print('   flask-sqlalchemy ', m.version('flask-sqlalchemy')); print('   flask-jwt-extended', m.version('flask-jwt-extended'))" 2>nul
echo.
echo Now double-click start.bat to launch the server.
pause
exit /b 0
