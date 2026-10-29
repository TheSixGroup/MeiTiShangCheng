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

from flask import Flask, send_from_directory, request, make_response
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

    # ---------- 静态托管：前端页面（与 API 同源，一条隧道即可同时访问页面和接口） ----------
    # 合并后本文件位于 <repo>/backend/app.py。前端目录可能在仓库内，也可能在仓库同级，
    # 依次探测并取第一个存在的；都不存在时回落到 <repo>/frontend，便于之后把前端放进来。
    _repo_root = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
    _frontend_candidates = [
        os.path.join(_repo_root, "frontend"),
        os.path.abspath(os.path.join(_repo_root, "..", "frontend")),
    ]
    FRONTEND_DIR = next(
        (p for p in _frontend_candidates if os.path.isdir(p)), _frontend_candidates[0]
    )

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "admin/login.html")

    @app.route("/<path:filename>")
    def frontend_static(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    # ---------- 健康检查 ----------
    @app.route("/api/v1/health")
    def health():
        return {"code": 0, "message": "success", "data": {"status": "ok"}}

    # ---------- CORS 跨域支持 ----------
    # 前后端分离 + 内网穿透场景：前端在别的电脑/域名访问后端时必须允许跨域。
    # 浏览器会先发 OPTIONS 预检请求，这里统一放行并回填 CORS 响应头。
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response

    @app.route("/api/v1/<path:_any>", methods=["OPTIONS"])
    def _cors_preflight(_any=None):
        """兜底处理 OPTIONS 预检请求，直接返回 204。"""
        return make_response("", 204)
    # ---------- 建表（首次运行自动创建） ----------
    with app.app_context():
        import models  # noqa: F401  确保模型注册到 metadata
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    # 端口 5000，开启调试便于开发（生产用 gunicorn/uwsgi）
    app.run(host="0.0.0.0", port=5000, debug=True)
