# -*- coding: utf-8 -*-
"""
统计报表模块 —— 契约文档第 7 章。

接口：
- GET /api/v1/stats/workforce              人力统计总览（stats:view）
- GET /api/v1/stats/employee/{id}/hours   员工工时统计
- GET /api/v1/stats/inventory             库存统计（stats:view）

指标口径见需求文档 7.1 / 7 节：
- 缺勤率 = 请假天数 / 计划工作日（简化：以请假审批通过比例近似）
- 工资成本 = 周排班总工时 × 时薪
"""
from datetime import date, datetime, timedelta

from flask import request
from flask_restx import Namespace, Resource

from common.auth import login_required, require_permission
from common.errors import ApiError, ERR_NOT_FOUND, ERR_PARAM
from common.response import success

ns = Namespace("stats", description="统计报表")


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(ERR_PARAM, f"日期格式错误：{s}")


@ns.route("/workforce")
class Workforce(Resource):
    """GET /stats/workforce —— 人力统计总览。"""

    @ns.doc("人力统计总览")
    @require_permission("stats:view")
    def get(self):
        """查询参数：startDate, endDate（缺省为本月）。

        返回 totalEmployees、activeEmployees、员工类型分布、
        人员趋势等（契约 7 章结构）。
        """
        from models import Employee, Schedule, Leave, EmployeeType

        employees = Employee.query.all()
        total = len(employees)
        active = len([e for e in employees if e.status == "active"])

        # 员工类型分布
        type_dist = {}
        for e in employees:
            type_dist[e.employee_type] = type_dist.get(e.employee_type, 0) + 1
        employee_type_distribution = [
            {"type": k, "count": v} for k, v in type_dist.items()
        ]

        # 时间范围
        start = _parse_date(request.args.get("startDate"))
        end = _parse_date(request.args.get("endDate"))
        if not start or not end:
            today = date.today()
            start = today.replace(day=1)
            end = today

        schedules = (Schedule.query
                     .filter(Schedule.work_date.between(start, end))
                     .filter(Schedule.status != "cancelled")
                     .all())
        planned_hours = sum(s.shift.hours for s in schedules if s.shift)

        # 工资成本（按排班工时 × 时薪汇总）
        wage_cost = sum(
            (s.shift.hours if s.shift else 0) * (s.employee.hourly_wage if s.employee else 0)
            for s in schedules
        )

        # 缺勤率：审批通过的请假天数 / (在职人数 × 统计天数)，取近似
        approved_leaves = (Leave.query
                           .filter_by(status="approved")
                           .filter(Leave.start_date >= start)
                           .filter(Leave.end_date <= end)
                           .all())
        leave_days = sum(l.days for l in approved_leaves)
        span_days = max((end - start).days + 1, 1)
        absence_rate = round(leave_days / (max(active, 1) * span_days), 4)

        # 人员趋势（按月统计在职人数，简化取入职日期）
        trend = {}
        for e in employees:
            if e.hire_date:
                key = e.hire_date.strftime("%Y-%m")
                trend[key] = trend.get(key, 0) + 1
        headcount_trend = [{"month": k, "count": v} for k, v in sorted(trend.items())]

        return success({
            "totalEmployees": total,
            "activeEmployees": active,
            "plannedHours": round(planned_hours, 2),
            "actualHours": round(planned_hours, 2),
            "absenceRate": absence_rate,
            "turnoverRate": round(len([e for e in employees if e.status == "resigned"]) / max(total, 1), 4),
            "wageCost": round(wage_cost, 2),
            "headcountTrend": headcount_trend,
            "employeeTypeDistribution": employee_type_distribution,
        })


@ns.route("/employee/<string:emp_id>/hours")
class EmployeeHours(Resource):
    """GET /stats/employee/{id}/hours —— 员工工时统计。"""

    @ns.doc("员工工时统计")
    @login_required
    def get(self, emp_id):
        """查询参数：month（YYYY-MM）或 startDate/endDate。"""
        from models import Employee, Schedule

        emp = Employee.query.get(emp_id)
        if not emp:
            raise ApiError(ERR_NOT_FOUND, "员工不存在")

        month = request.args.get("month")
        if month:
            try:
                y, m = map(int, month.split("-"))
            except (ValueError, AttributeError):
                raise ApiError(ERR_PARAM, "month 格式应为 YYYY-MM")
            import calendar
            start = date(y, m, 1)
            end = date(y, m, calendar.monthrange(y, m)[1])
        else:
            start = _parse_date(request.args.get("startDate"))
            end = _parse_date(request.args.get("endDate"))
            if not start or not end:
                today = date.today()
                start = today.replace(day=1)
                end = today

        rows = (Schedule.query
                .filter_by(employee_id=emp_id)
                .filter(Schedule.work_date.between(start, end))
                .filter(Schedule.status != "cancelled")
                .order_by(Schedule.work_date)
                .all())

        daily = {}
        for r in rows:
            daily[r.work_date] = r.shift.hours if r.shift else 0

        total_hours = sum(daily.values())
        working_days = len(daily)

        # 按周分组
        weekly = {}
        for d, h in daily.items():
            ws = d - timedelta(days=d.weekday())
            weekly[ws] = weekly.get(ws, 0) + h
        weekly_breakdown = [
            {"week": f"第{i+1}周", "weekStart": ws.strftime("%Y-%m-%d"), "hours": h}
            for i, (ws, h) in enumerate(sorted(weekly.items()))
        ]

        daily_breakdown = [
            {"date": d.strftime("%Y-%m-%d"), "hours": h}
            for d, h in sorted(daily.items())
        ]

        return success({
            "totalHours": round(total_hours, 2),
            "workingDays": working_days,
            "averageHoursPerDay": round(total_hours / working_days, 2) if working_days else 0,
            "overtimeHours": round(max(total_hours - 40 * len(weekly), 0), 2),
            "weeklyBreakdown": weekly_breakdown,
            "dailyBreakdown": daily_breakdown,
        })


@ns.route("/inventory")
class InventoryStats(Resource):
    """GET /stats/inventory —— 库存统计。"""

    @ns.doc("库存统计")
    @require_permission("stats:view")
    def get(self):
        """返回总 SKU 数、低库存数、缺货数、分类占比。"""
        from models import Product

        products = Product.query.all()
        statuses = [p.calc_status() for p in products]

        category = {}
        for p in products:
            cat = p.category_name or "未分类"
            category[cat] = category.get(cat, 0) + p.stock_quantity

        return success({
            "totalSku": len(products),
            "lowStockCount": statuses.count("low_stock"),
            "outOfStockCount": statuses.count("out_of_stock"),
            "categoryStock": [{"category": k, "quantity": v} for k, v in category.items()],
        })