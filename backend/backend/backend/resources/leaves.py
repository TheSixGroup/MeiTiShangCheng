# -*- coding: utf-8 -*-
"""
请假管理模块 —— 契约文档第 5 章 + 需求文档第 5 节。

接口：
- GET  /api/v1/leaves/my           获取我的请假记录
- POST /api/v1/leaves              提交请假申请
- GET  /api/v1/leaves              请假申请列表（管理端，leave:approve）
- PUT  /api/v1/leaves/{id}/approve 审批请假申请（leave:approve）

业务规则（需求 5.1）：
- sick 病假：从 sickLeaveDays 扣减
- annual 年假：从 annualLeaveDays 扣减
- personal 事假：无薪，不扣假期天数
审批通过后才扣减；拒绝不扣。
"""
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource

from common.auth import current_user, current_employee_id, login_required, require_permission
from common.errors import ApiError, ERR_PARAM, ERR_NOT_FOUND, ERR_BUSINESS
from common.response import success, paged

ns = Namespace("leaves", description="考勤与请假")


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(ERR_PARAM, f"日期格式错误：{s}")


@ns.route("/my")
class MyLeaves(Resource):
    """GET /leaves/my —— 当前用户自己的请假记录。"""

    @ns.doc("获取我的请假记录")
    @login_required
    def get(self):
        """查询参数：page, pageSize, status。"""
        from models import Leave

        emp_id = current_employee_id()
        if not emp_id:
            return success({"list": [], "total": 0, "page": 1, "pageSize": 10})

        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("pageSize", 10)), 1), 100)
        status = request.args.get("status")

        query = Leave.query.filter_by(employee_id=emp_id)
        if status:
            query = query.filter_by(status=status)
        total = query.count()
        rows = (query.order_by(Leave.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size).all())
        return paged([r.to_dict() for r in rows], total, page, page_size)


@ns.route("")
class LeaveList(Resource):
    """GET /leaves 列表（管理端）；POST /leaves 提交申请。"""

    @ns.doc("获取请假申请列表（管理端）")
    @require_permission("leave:approve")
    def get(self):
        """查询参数：page, pageSize, status, employeeId。"""
        from models import Leave

        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("pageSize", 10)), 1), 100)
        status = request.args.get("status")
        employee_id = request.args.get("employeeId")

        query = Leave.query
        if status:
            query = query.filter_by(status=status)
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        total = query.count()
        rows = (query.order_by(Leave.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size).all())
        return paged([r.to_dict() for r in rows], total, page, page_size)

    @ns.doc("提交请假申请")
    @login_required
    def post(self):
        """请求体：{ leaveType, startDate, endDate, reason }。

        员工本人提交。天数按自然日计算（含首尾）。
        """
        from models import Leave, Employee
        from extensions import db

        emp_id = current_employee_id()
        if not emp_id:
            raise ApiError(ERR_PARAM, "当前账号未关联员工信息")

        body = request.get_json(silent=True) or {}
        leave_type = body.get("leaveType")
        start = _parse_date(body.get("startDate"))
        end = _parse_date(body.get("endDate"))
        if leave_type not in ("sick", "annual", "personal"):
            raise ApiError(ERR_PARAM, "leaveType 只能是 sick / annual / personal")
        if not start or not end:
            raise ApiError(ERR_PARAM, "startDate 和 endDate 为必填")
        if end < start:
            raise ApiError(ERR_PARAM, "结束日期不能早于开始日期")

        days = (end - start).days + 1

        # 校验剩余假期（需求 5.1）
        emp = Employee.query.get(emp_id)
        if leave_type == "sick" and days > emp.sick_leave_days:
            raise ApiError(ERR_BUSINESS, f"剩余病假不足，仅剩 {emp.sick_leave_days} 天")
        if leave_type == "annual" and days > emp.annual_leave_days:
            raise ApiError(ERR_BUSINESS, f"剩余年假不足，仅剩 {emp.annual_leave_days} 天")

        leave = Leave(
            employee_id=emp_id,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            days=days,
            reason=body.get("reason", ""),
            status="pending",
        )
        db.session.add(leave)
        db.session.commit()
        return success(leave.to_dict(), "请假申请已提交")


@ns.route("/<string:leave_id>/approve")
class Approve(Resource):
    """PUT /leaves/{id}/approve —— 审批请假。"""

    @ns.doc("审批请假申请")
    @require_permission("leave:approve")
    def put(self, leave_id):
        """请求体：{ status: approved|rejected, comment }。

        通过时扣减对应假期天数（需求 5.1）：
        - sick 扣 sickLeaveDays
        - annual 扣 annualLeaveDays
        - personal 不扣
        """
        from models import Leave, Employee
        from extensions import db

        leave = Leave.query.get(leave_id)
        if not leave:
            raise ApiError(ERR_NOT_FOUND, "请假申请不存在")
        if leave.status != "pending":
            raise ApiError(ERR_BUSINESS, "该申请已处理，不能重复审批")

        body = request.get_json(silent=True) or {}
        new_status = body.get("status")
        if new_status not in ("approved", "rejected"):
            raise ApiError(ERR_PARAM, "status 只能是 approved 或 rejected")

        user = current_user()
        leave.status = new_status
        leave.approver_id = user.employee_id if user else None
        leave.approved_at = datetime.now()
        leave.comment = body.get("comment", "")

        # 仅在通过时扣减假期
        if new_status == "approved":
            emp = Employee.query.get(leave.employee_id)
            if emp:
                if leave.leave_type == "sick":
                    emp.sick_leave_days = max(0, emp.sick_leave_days - leave.days)
                elif leave.leave_type == "annual":
                    emp.annual_leave_days = max(0, emp.annual_leave_days - leave.days)

        db.session.commit()
        return success(leave.to_dict(), "审批完成")