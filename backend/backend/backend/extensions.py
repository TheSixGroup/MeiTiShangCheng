# -*- coding: utf-8 -*-
"""
扩展初始化模块 —— 只负责创建扩展实例，不在此处绑定 app。

好处：避免循环导入（models 导入 db，app 也导入 db）。
绑定动作统一在 app.py 里通过 init_app() 完成。
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# ORM 实例
db = SQLAlchemy()

# JWT 认证管理器
jwt = JWTManager()