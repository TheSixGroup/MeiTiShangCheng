# -*- coding: utf-8 -*-
"""
员工管理模块 —— 契约文档第 3 章。

接口：
- GET    /api/v1/employees                     分页列表
- GET    /api/v1/employees/available-for-shift 可排班员工
- GET    /api/v1/employees/{id}                详情
- POST   /api/v1/employees                     新增（employee:add）
- PUT    /api/v1/employees/{id}                更新（employee:edit）
- DELETE /api/v1/employees/{id}                软删除（employee:delete）

字段级权限（需求文档 2.3）：hourlyWage 等敏感字段仅 hr_officer
与 manager 可见，其他角色不返回。
"""
from datetime import date, datetime, timedelta

from flask import request
from flask_restx import Namespace, Resource
from sqlalchemy import or_

from common.auth import current_user, login_required, require_permission, can_see_sensitive
from common.errors import ApiError, ERR_PARAM, ERR_NOT_FOUND, ERR_CONFLICT
from common.response import success, paged

ns = Namespace("employees", description="员工管理")


def _parse_date(s):
    """解析 'YYYY-MM-DD'，空值返回 None，非法抛 1001。"""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(ERR_PARAM, f"日期格式错误：{s}，应为 YYYY-MM-DD")


def _get_employee_or_404(eid: str):
    from models import Employee
    emp = Employee.query.get(eid)
    if not emp:
        raise ApiError(ERR_NOT_FOUND, "员工不存在")
    return emp


@ns.route("")
class EmployeeList(Resource):
    """GET /employees 分页列表；POST /employees 新增。"""

    @ns.doc("获取员工列表（分页）")
    @login_required
    def get(self):
        """查询参数：page, pageSize, keyword, employeeType, status, departmentId。

        默认只展示 active 员工（需求文档 3 节），
        通过 status 参数可筛选已离职等状态。
        """
        from models import Employee

        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(max(int(request.args.get("pageSize", 10)), 1), 100)
        keyword = (request.args.get("keyword") or "").strip()
        employee_type = request.args.get("employeeType")
        status = request.args.get("status")
        department_id = request.args.get("departmentId")

        query = Employee.query
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(Employee.real_name.like(like), Employee.employee_no.like(like))
            )
        if employee_type:
            query = query.filter(Employee.employee_type == employee_type)
        if status:
            query = query.filter(Employee.status == status)
        if department_id:
            query = query.filter(Employee.department_id == department_id)

        total = query.count()
        rows = (query.order_by(Employee.created_at.desc())
                .offset((page - 1) * page_size).limit(page_size).all())

        show_sensitive = can_see_sensitive()
        items = [e.to_dict(include_sensitive=show_sensitive) for e in rows]
        return paged(items, total, page, page_size)

    @ns.doc("新增员工")
    @require_permission("employee:add")
    def post(self):
        """新增员工（契约 3.1）。

        请求体字段见契约 3.1；password 为登录初始密码（默认 123456）。
        员工编号重复返回 3003。
        """
        from models import Employee, User, EmployeeType
        from extensions import db

        body = request.get_json(silent=True) or {}
        employee_no = (body.get("employeeNo") or "").strip()
        real_name = (body.get("realName") or "").strip()
        if not employee_no or not real_name:
            raise ApiError(ERR_PARAM, "员工编号和姓名不能为空")
        if Employee.query.filter_by(employee_no=employee_no).first():
            raise ApiError(ERR_CONFLICT, f"员工编号已存在：{employee_no}")

        # 时薪：未显式给出则取员工类型默认时薪
        hourly_wage = body.get("hourlyWage")
        if hourly_wage is None:
            et = EmployeeType.query.filter_by(code=body.get("employeeType", "fulltime")).first()
            hourly_wage = et.default_hourly_wage if et else 0.0

        emp = Employee(
            employee_no=employee_no,
            real_name=real_name,
            gender=body.get("gender", "male"),
            phone=body.get("phone", ""),
            email=body.get("email", ""),
            employee_type=body.get("employeeType", "fulltime"),
            department_id=body.get("departmentId") or None,
            position=body.get("position", ""),
            hourly_wage=hourly_wage,
            hire_date=_parse_date(body.get("hireDate")) or date.today(),
            roles=",".join(body.get("roles") or ["employee"]),
        )
        db.session.add(emp)
        db.session.flush()  # 拿到 emp.id

        # 创建登录账号
        username = (body.get("username") or employee_no).strip()
        if User.query.filter_by(username=username).first():
            raise ApiError(ERR_CONFLICT, f"登录用户名已存在：{username}")
        account = User(
            username=username,
            employee_id=emp.id,
            roles=",".join(body.get("roles") or ["employee"]),
        )
        account.set_password(body.get("password") or "123456")
        db.session.add(account)
        db.session.commit()

        return success(emp.to_dict(include_sensitive=True), "新增员工成功")


@ns.route("/available-for-shift")
class AvailableForShift(Resource):
    """GET /employees/available-for-shift —— 指定日期/班次可安排员工。

    注意：该静态路由必须定义在 /{id} 之前，避免被 id 匹配。
    """

    @ns.doc("获取可排班员工列表")
    @login_required
    def get(self):
        """查询参数：date, shiftId。

        返回在职员工，并附当周已排班天数（用于冲突与超限提示）。
        """
        from models import Employee, Schedule, Shift

        d = _parse_date(request.args.get("date"))
        if not d:
            raise ApiError(ERR_PARAM, "缺少参数 date")

        # 计算周一日期
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)

        employees = Employee.query.filter_by(status="active").all()
        result = []
        for emp in employees:
            # 当天已排班则排除（同一员工一天只能排 1 个班次，需求 4.3）
            same_day = Schedule.query.filter_by(
                employee_id=emp.id, work_date=d
            ).filter(Schedule.status != "cancelled").first()
            if same_day:
                continue
            # 当周已工作天数
            week_days = (Schedule.query
                         .filter(Schedule.employee_id == emp.id)
                         .filter(Schedule.work_date.between(week_start, week_end))
                         .filter(Schedule.status != "cancelled")
                         .with_entities(Schedule.work_date).distinct().count())
            item = emp.to_dict(include_sensitive=can_see_sensitive())
            item["weekWorkDays"] = week_days
            result.append(item)
        return success(result)


@ns.route("/<string:eid>")
class EmployeeItem(Resource):
    """GET/PUT/DELETE /employees/{id}。"""

    @ns.doc("获取员工详情")
    @login_required
    def get(self, eid):
        emp = _get_employee_or_404(eid)
        return success(emp.to_dict(include_sensitive=can_see_sensitive()))

    @ns.doc("更新员工信息")
    @require_permission("employee:edit")
    def put(self, eid):
        """全量更新员工信息（不含密码，密码走 auth 单独接口）。"""
        from extensions import db

        emp = _get_employee_or_404(eid)
        body = request.get_json(silent=True) or {}

        if "realName" in body:
            emp.real_name = body["realName"]
        if "gender" in body:
            emp.gender = body["gender"]
        if "phone" in body:
            emp.phone = body["phone"]
        if "email" in body:
            emp.email = body["email"]
        if "employeeType" in body:
            emp.employee_type = body["employeeType"]
        if "departmentId" in body:
            emp.department_id = body["departmentId"] or None
        if "position" in body:
            emp.position = body["position"]
        if "hourlyWage" in body:
            emp.hourly_wage = body["hourlyWage"]
        if "hireDate" in body:
            emp.hire_date = _parse_date(body["hireDate"])
        if "status" in body:
            emp.status = body["status"]
        if "roles" in body:
            emp.roles = ",".join(body["roles"])
            if emp.account:
                emp.account.roles = emp.roles

        db.session.commit()
        return success(emp.to_dict(include_sensitive=True), "更新成功")

    @ns.doc("删除员工（离职）")
    @require_permission("employee:delete")
    def delete(self, eid):
        """软删除：status 置为 resigned 并记录 leaveDate（契约 3 节）。"""
        from extensions import db

        emp = _get_employee_or_404(eid)
        emp.status = "resigned"
        emp.leave_date = date.today()
        db.session.commit()
        return success(None, "员工已标记离职")
