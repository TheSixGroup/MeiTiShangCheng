# -*- coding: utf-8 -*-
"""
业务错误码与异常处理 —— 契约文档 1.6 节。

错误码与 HTTP 状态码映射（以契约文档 v1.0 为准）：
| code | HTTP | 含义 |
|------|------|------|
| 0    | 200  | 成功 |
| 1001 | 400  | 参数校验错误 |
| 1002 | 400  | 请求格式错误 |
| 2001 | 401  | 未登录 / Token 缺失 |
| 2002 | 401  | Token 已过期 |
| 2003 | 403  | 无权限访问 |
| 3001 | 404  | 资源不存在 |
| 3002 | 400  | 用户名或密码错误 |
| 3003 | 409  | 资源已存在（如员工编号重复） |
| 4001 | 400  | 业务逻辑错误（如排班冲突） |
| 5000 | 500  | 服务器内部错误 |

注意：需求确认文档 1.2 节是精简版错误码表，本实现以接口契约文档 1.6 节为准。
"""
from flask import Flask


# ---------- 业务错误码常量 ----------
ERR_SUCCESS = 0
ERR_PARAM = 1001
ERR_FORMAT = 1002
ERR_UNAUTH = 2001
ERR_TOKEN_EXPIRED = 2002
ERR_NO_PERM = 2003
ERR_NOT_FOUND = 3001
ERR_BAD_CREDENTIALS = 3002
ERR_CONFLICT = 3003
ERR_BUSINESS = 4001
ERR_SERVER = 5000


# 错误码 -> HTTP 状态码
HTTP_STATUS = {
    ERR_PARAM: 400,
    ERR_FORMAT: 400,
    ERR_UNAUTH: 401,
    ERR_TOKEN_EXPIRED: 401,
    ERR_NO_PERM: 403,
    ERR_NOT_FOUND: 404,
    ERR_BAD_CREDENTIALS: 400,
    ERR_CONFLICT: 409,
    ERR_BUSINESS: 400,
    ERR_SERVER: 500,
}


class ApiError(Exception):
    """业务异常。

    业务层抛出该异常，由全局错误处理器统一转成标准响应，
    避免每个资源都写 try/except 拼响应。

    用法：
        raise ApiError(ERR_NOT_FOUND, "员工不存在")
    """

    def __init__(self, code: int, message: str, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status or HTTP_STATUS.get(code, 400)


# 便捷构造器
def bad_request(msg="参数校验错误"):
    return ApiError(ERR_PARAM, msg)


def not_found(msg="资源不存在"):
    return ApiError(ERR_NOT_FOUND, msg)


def conflict(msg="资源已存在"):
    return ApiError(ERR_CONFLICT, msg)


def business_error(msg="业务逻辑错误"):
    return ApiError(ERR_BUSINESS, msg)


def forbidden(msg="无权限访问"):
    return ApiError(ERR_NO_PERM, msg)


# ============================================================
# 全局异常注册
# ============================================================
def register_error_handlers(app: Flask) -> None:
    """在 app 上注册全局错误处理器。

    - ApiError：业务异常 → 标准错误响应
    - 404/405：Flask 路由级错误 → 标准错误响应
    - 其他未捕获异常 → 5000
    """
    from common.response import error as build_error

    @app.errorhandler(ApiError)
    def _handle_api_error(e: ApiError):
        return build_error(e.code, e.message, e.http_status)

    @app.errorhandler(404)
    def _handle_404(e):
        return build_error(ERR_NOT_FOUND, "接口不存在", 404)

    @app.errorhandler(405)
    def _handle_405(e):
        return build_error(ERR_PARAM, "请求方法不允许", 405)

    @app.errorhandler(Exception)
    def _handle_unknown(e: Exception):
        # 开发阶段把真实异常打印到控制台，方便排查
        import traceback
        traceback.print_exc()
        return build_error(ERR_SERVER, "服务器内部错误", 500)