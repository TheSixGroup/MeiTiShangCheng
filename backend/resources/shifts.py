# -*- coding: utf-8 -*-
"""
班次定义模块 —— 契约文档 4.1 节。

接口：
- GET /api/v1/shifts  获取所有班次定义（早班/中班/晚班）

班次为固定三种（需求文档 C5 / 4.1），不支持自定义时间。
"""
from flask_restx import Namespace, Resource

from common.auth import login_required
from common.response import success

ns = Namespace("shifts", description="班次定义")


@ns.route("")
class ShiftList(Resource):
    """GET /shifts —— 获取所有班次定义。"""

    @ns.doc("获取所有班次定义")
    @login_required
    def get(self):
        """返回班次定义数组（契约 4.1 节）。"""
        from models import Shift

        shifts = Shift.query.order_by(Shift.start_time).all()
        return success([s.to_dict() for s in shifts])