# -*- coding: utf-8 -*-
"""
应用入口 —— 美体商城员工管理系统 后端。

启动方式（在项目根目录）：
    .venv\\Scripts\\python.exe backend\\app.py

默认端口 5000（需求文档 8.1）。
Swagger 文档：http://localhost:5000/api/docs
BaseURL：http://localhost:5000/api/v1

应用工厂模式：create_app() 便于测试与多环境。
"""
import os
import sys

# 把 backend 目录加入模块搜索路径，保证从任意工作目录运行都能 import
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from flask import Flask, send_from_directory
from flask_restx import Api

from config import Config
from extensions import db, jwt
from common.errors import register_error_handlers
from common.auth import register_jwt_handlers
from resources import register_resources


def create_app() -> Flask:
    """创建并配置 Flask 应用。"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---------- 初始化扩展 ----------
    db.init_app(app)
    jwt.init_app(app)

    # ---------- 注册 JWT 错误回调（2001/2002） ----------
    register_jwt_handlers(jwt)

    # ---------- 全局异常处理（统一错误结构） ----------
    register_error_handlers(app)

    # ---------- RESTX API（BaseURL /api/v1，Swagger /api/docs） ----------
    api = Api(
        app,
        version="1.0",
        title="美体商城员工管理系统 API",
        description="前后端接口契约文档 v1.0 的后端实现",
        doc="/api/docs",
        prefix="/api/v1",
    )

    # 注册各业务命名空间
    register_resources(api)

    # ---------- 静态文件：上传文件访问 ----------
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        """提供上传文件的静态访问（返回文件流，不套 API 响应结构）。"""
        return send_from_directory(os.path.join(app.root_path, "uploads"), filename)

    # ---------- 健康检查 ----------
    @app.route("/api/v1/health")
    def health():
        return {"code": 0, "message": "success", "data": {"status": "ok"}}

    # ---------- 建表（首次运行自动创建） ----------
    with app.app_context():
        import models  # noqa: F401  确保模型注册到 metadata
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    # 端口 5000，开启调试便于开发（生产用 gunicorn/uwsgi）
    app.run(host="0.0.0.0", port=5000, debug=True)