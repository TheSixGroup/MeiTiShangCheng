# -*- coding: utf-8 -*-
"""
认证与权限 —— 契约文档 1.4 节 + 需求文档 2.2 权限矩阵。

设计要点：
- JWT 的 identity 存 user_id（字符串）。
- 每次请求通过 current_user() 现查数据库，保证权限即时生效。
- Token 缺失返回 2001，过期返回 2002（契约 1.4）。
- 权限控制：前端按 permissions 显隐菜单，后端二次校验（契约 1.4）。

提供的工具：
- current_user()：取当前登录用户（未登录返回 None）
- login_required：装饰器，要求登录
- require_permission(code)：装饰器，要求某权限码
- require_roles(*roles)：装饰器，要求某角色
"""
from functools import wraps

from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from common.errors import ApiError, ERR_UNAUTH, ERR_NO_PERM, ERR_TOKEN_EXPIRED


# ============================================================
# JWT 错误处理（在 extensions 注册）
# ============================================================
def register_jwt_handlers(jwt) -> None:
    """注册 JWT 错误回调，把底层错误映射成契约错误码。

    - Token 缺失 / 无效：2001
    - Token 过期：2002
    - 权限不足由 require_permission 抛出：2003
    """
    from common.response import error as build_error

    @jwt.unauthorized_loader
    def _missing_token(reason):
        return build_error(ERR_UNAUTH, "未登录或 Token 缺失", 401)

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return build_error(ERR_UNAUTH, "Token 无效", 401)

    @jwt.expired_token_loader
    def _expired_token(header, payload):
        return build_error(ERR_TOKEN_EXPIRED, "Token 已过期，请重新登录", 401)


# ============================================================
# 当前用户
# ============================================================
def current_user():
    """获取当前登录的 User 对象；未登录或无 identity 时返回 None。"""
    if hasattr(g, "_current_user"):
        return g._current_user
    uid = get_jwt_identity()
    user = None
    if uid:
        from models import User
        user = User.query.get(uid)
    g._current_user = user
    return user


def require_user():
    """获取当前用户，不存在则抛 2001。"""
    user = current_user()
    if not user:
        raise ApiError(ERR_UNAUTH, "用户不存在或未登录", 401)
    return user


def current_employee_id() -> str | None:
    """当前用户关联的 employeeId（用于员工自助接口）。"""
    user = current_user()
    return user.employee_id if user else None


# ============================================================
# 装饰器
# ============================================================
def login_required(fn):
    """要求登录。校验 JWT 并在失败时抛标准错误。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if current_user() is None:
            raise ApiError(ERR_UNAUTH, "用户不存在", 401)
        return fn(*args, **kwargs)

    return wrapper


def require_permission(code: str):
    """要求某项权限码（契约 8.2 节权限码清单）。

    用法：
        @require_permission("employee:add")
        def post(self): ...
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if user is None:
                raise ApiError(ERR_UNAUTH, "用户不存在", 401)
            if code not in user.permissions():
                raise ApiError(ERR_NO_PERM, f"无权限访问：{code}", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_roles(*roles):
    """要求用户拥有指定角色之一。

    用法：
        @require_roles("hr_officer", "manager")
        def post(self): ...
    """
    wanted = set(roles)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if user is None:
                raise ApiError(ERR_UNAUTH, "用户不存在", 401)
            if not wanted.intersection(user.role_list()):
                raise ApiError(ERR_NO_PERM, "无权限访问", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def can_see_sensitive() -> bool:
    """当前用户是否可查看敏感字段（hourlyWage 等），需求文档 2.3 节。"""
    user = current_user()
    if not user:
        return False
    return bool({"hr_officer", "manager"} & set(user.role_list()))