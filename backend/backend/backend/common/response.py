# -*- coding: utf-8 -*-
"""
统一响应结构 —— 契约文档 1.2 / 1.3 节。

所有接口都通过本模块构造返回值，保证：
- 成功：{ "code": 0, "message": "success", "data": ... }
- 失败：{ "code": <业务码>, "message": "<描述>", "data": null }
- 分页：data = { list, total, page, pageSize }

资源层只需返回 dict，由 app.py 的 after_request 兜底包装；
或显式调用 success()/paged() 构造，二选一统一即可。
"""


def success(data=None, message: str = "success") -> tuple:
    """构造成功响应。

    :param data: 响应数据（对象/数组/None）
    :param message: 提示信息，成功默认 "success"
    :return: (body_dict, http_status) 二元组
    """
    return {"code": 0, "message": message, "data": data}, 200


def paged(items: list, total: int, page: int, page_size: int) -> tuple:
    """构造分页成功响应（契约 1.3 节）。

    :param items: 当前页数据列表
    :param total: 总记录数
    :param page: 当前页码（从 1 开始）
    :param page_size: 每页条数
    """
    return success({
        "list": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    })


def error(code: int, message: str, http_status: int = 400) -> tuple:
    """构造错误响应。

    :param code: 业务错误码（见 common/errors.py）
    :param message: 错误描述
    :param http_status: HTTP 状态码
    """
    return {"code": code, "message": message, "data": None}, http_status