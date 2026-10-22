# -*- coding: utf-8 -*-
"""
资源层包 —— 所有 RESTX Namespace（按契约文档模块划分）。

提供 register_resources(api) 统一把各模块的命名空间挂到 api 上，
app.py 只需调用一次。
"""


def register_resources(api):
    """把所有业务模块的 Namespace 注册到 api 对象。"""
    from resources.auth import ns as auth_ns
    from resources.employees import ns as employees_ns
    from resources.shifts import ns as shifts_ns
    from resources.schedules import ns as schedules_ns
    from resources.leaves import ns as leaves_ns
    from resources.inventory import ns as inventory_ns
    from resources.restock import ns as restock_ns
    from resources.stats import ns as stats_ns
    from resources.files import ns as files_ns

    api.add_namespace(auth_ns, path="/auth")
    api.add_namespace(employees_ns, path="/employees")
    api.add_namespace(shifts_ns, path="/shifts")
    api.add_namespace(schedules_ns, path="/schedules")
    api.add_namespace(leaves_ns, path="/leaves")
    api.add_namespace(inventory_ns, path="/inventory")
    api.add_namespace(restock_ns, path="/restock-requests")
    api.add_namespace(stats_ns, path="/stats")
    api.add_namespace(files_ns, path="/files")