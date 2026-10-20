# -*- coding: utf-8 -*-
"""
认证模块 —— 契约文档第 2 章。

接口：
- POST /api/v1/auth/login      登录（无需认证）
- POST /api/v1/auth/logout     登出（需认证）
- GET  /api/v1/auth/me         获取当前用户信息（需认证）
- PUT  /api/v1/auth/password   修改密码（需认证）

认证采用 JWT，登录成功返回 token + userInfo（契约 1.4）。
"""
from flask import request
from flask_restx import Namespace, Resource

from common.auth import current_user, login_required
from common.errors import ApiError, ERR_BAD_CREDENTIALS, ERR_PARAM, ERR_NOT_FOUND
from common.response import success

ns = Namespace("auth", description="认证与账号")


@ns.route("/login")
class Login(Resource):
    """POST /auth/login —— 登录。"""

    @ns.doc("登录")
    def post(self):
        """校验用户名密码，返回 token 与用户信息（契约 1.4 节）。

        请求体：
            { "username": "zhangsan", "password": "123456" }
        响应 data：
            { "token": "...", "userInfo": { ... } }
        """
        from flask_jwt_extended import create_access_token
        from models import User

        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if not username or not password:
            raise ApiError(ERR_PARAM, "用户名和密码不能为空")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            # 契约 3002：用户名或密码错误
            raise ApiError(ERR_BAD_CREDENTIALS, "用户名或密码错误")

        token = create_access_token(identity=user.id)
        return success({
            "token": token,
            "userInfo": user.to_userinfo(),
        })


@ns.route("/logout")
class Logout(Resource):
    """POST /auth/logout —— 登出。"""

    @ns.doc("登出")
    @login_required
    def post(self):
        """JWT 无状态，服务端不保存会话；前端丢弃 token 即可。

        本接口仅用于前端统一调用入口，返回 data=null。
        """
        return success(None)


@ns.route("/me")
class Me(Resource):
    """GET /auth/me —— 获取当前用户信息。"""

    @ns.doc("获取当前用户信息")
    @login_required
    def get(self):
        """返回当前登录用户信息（结构同登录返回的 userInfo）。"""
        user = current_user()
        return success(user.to_userinfo())


@ns.route("/password")
class Password(Resource):
    """PUT /auth/password —— 修改密码。"""

    @ns.doc("修改密码")
    @login_required
    def put(self):
        """修改当前用户密码。

        请求体：
            { "oldPassword": "123456", "newPassword": "abc123" }
        """
        user = current_user()
        body = request.get_json(silent=True) or {}
        old = body.get("oldPassword") or ""
        new = body.get("newPassword") or ""
        if not old or not new:
            raise ApiError(ERR_PARAM, "旧密码和新密码不能为空")
        if not user.check_password(old):
            raise ApiError(ERR_BAD_CREDENTIALS, "旧密码错误")
        if len(new) < 6:
            raise ApiError(ERR_PARAM, "新密码长度不能少于 6 位")

        user.set_password(new)
        from extensions import db
        db.session.commit()
        return success(None)