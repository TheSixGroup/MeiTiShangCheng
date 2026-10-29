# -*- coding: utf-8 -*-
"""
扩展初始化模块 —— 只负责创建扩展实例，不在此处绑定 app。

好处：避免循环导入（models 导入 db，app 也导入 db）。
绑定动作统一在 app.py 里通过 init_app() 完成。
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from sqlalchemy import event
from sqlalchemy.engine import Engine

# ORM 实例
db = SQLAlchemy()

# JWT 认证管理器
jwt = JWTManager()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite 默认不启用外键约束：每条连接打开时显式开启。

    没有这一步，models 里声明的 FK 只是文档，插入非法引用不会报错。
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:          # 非 SQLite 连接（如 PostgreSQL）忽略
        pass
    finally:
        cursor.close()