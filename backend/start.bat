@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
    echo [错误] 未找到虚拟环境 .venv
    echo 请先执行: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo ========================================
echo  美体商城员工管理系统 - 后端启动
echo  Swagger 文档: http://localhost:5000/api/docs
echo ========================================

.venv\Scripts\python.exe backend\app.py
pause