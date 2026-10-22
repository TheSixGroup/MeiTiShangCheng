# -*- coding: utf-8 -*-
"""
配置模块 —— 集中管理应用配置。

根据接口契约文档 v1.0 及需求确认文档的约定：
- 后端端口 5000（需求文档 8.1 全局配置）
- BaseURL /api/v1
- 时区 UTC+8（Asia/Shanghai）

所有配置均可通过环境变量覆盖，方便部署。
"""
import os
from datetime import timedelta


class Config:
    """基础配置类，所有环境共享的默认配置。"""

    # ---------- 基础 ----------
    SECRET_KEY = os.environ.get("SECRET_KEY", "meiti-shangcheng-dev-secret")

    # ---------- 数据库（SQLite，零配置） ----------
    # 数据库文件放在 backend 目录下的 data.db
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "data.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # ---------- JWT 认证（契约文档 1.4 节） ----------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "meiti-shangcheng-jwt-secret")
    # Token 有效期：开发环境给 8 小时，方便调试
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    # 前端在 Header 中携带 Authorization: Bearer <token>
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"

    # ---------- RESTX / Swagger ----------
    # Swagger 文档地址 /api/docs（需求文档 8.1）
    RESTX_SWAGGER_UI_PATH = "/api/docs"

    # ---------- 业务常量 ----------
    # 一周起始日为周一（需求文档 8.1）
    # Python date.weekday(): Monday == 0
    WEEK_START_DAY = 0