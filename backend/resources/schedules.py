# -*- coding: utf-8 -*-
"""
排班管理模块 —— 契约文档第 4 章。

接口：
- GET    /api/v1/schedules/week                    周排班总览
- GET    /api/v1/schedules/employee/{employeeId}   员工个人周排班
- GET    /api/v1/schedules/month                   月排班日历
- POST   /api/v1/schedules/assign                  分配员工到班次（shift:assign）
- DELETE /api/v1/schedules/{scheduleId}            取消排班（shift:assign）
- POST   /api/v1/schedules/publish                 发布周排班（shift:publish）
- GET    /api/v1/schedules/export                  导出排班（CSV/PDF）

冲突检测规则（需求文档 4.3）：
1. 同一员工同一天不能排两个班次
2. 同一员工一周超过 5 天 -> 警告（允许强制确认）
3. 已离职员工不能排班

关于错误码（文档存在冲突，以契约文档 v1.0 为准）：
- 契约第 4 章写冲突返回 4001；契约 1.6 节中 3001=资源不存在(404)。
- 因此排班冲突统一使用 4001（业务逻辑错误，HTTP 400）。
"""
import csv
import io
from datetime import date, datetime, timedelta

from flask import request, Response
from flask_restx import Namespace, Resource

from common.auth import current_user, login_required, require_permission
from common.errors import ApiError, ERR_PARAM, ERR_NOT_FOUND, ERR_BUSINESS
from common.response import success

ns = Namespace("schedules", description="排班管理")

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(ERR_PARAM, f"日期格式错误：{s}，应为 YYYY-MM-DD")


def _week_start(d: date) -> date:
    """返回 d 所在周的周一。"""
    return d - timedelta(days=d.weekday())


def _all_shifts():
    from models import Shift
    return Shift.query.order_by(Shift.start_time).all()


# ============================================================
# 周排班总览
# ============================================================
@ns.route("/week")
class WeekOverview(Resource):
    """GET /schedules/week —— 获取周排班总览。"""

    @ns.doc("获取周排班总览")
    @login_required
    def get(self):
        """按日期分组返回一周的排班，每天含三个班次的员工列表（契约 4 章）。

        查询参数：weekStart（周一日期，YYYY-MM-DD，缺省为本周）。
        """
        from models import Schedule, Shift

        week_start = _parse_date(request.args.get("weekStart")) or _week_start(date.today())
        week_end = week_start + timedelta(days=6)

        shifts = _all_shifts()
        rows = (Schedule.query
                .filter(Schedule.work_date.between(week_start, week_end))
                .filter(Schedule.status != "cancelled")
                .all())

        # 按 日期 -> 班次 分组
        grouped = {}
        for r in rows:
            grouped.setdefault(r.work_date, {}).setdefault(r.shift_id, []).append(r.to_dict())

        days = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            day_shifts = []
            for sh in shifts:
                day_shifts.append({
                    "shiftId": sh.code,
                    "shiftName": sh.name,
                    "employees": grouped.get(d, {}).get(sh.id, []),
                })
            days.append({"date": d.strftime("%Y-%m-%d"), "weekday": WEEKDAYS[i], "shifts": day_shifts})

        return success({
            "weekStart": week_start.strftime("%Y-%m-%d"),
            "weekEnd": week_end.strftime("%Y-%m-%d"),
            "days": days,
        })


# ============================================================
# 员工个人周排班
# ============================================================
@ns.route("/employee/<string:employee_id>")
class EmployeeWeek(Resource):
    """GET /schedules/employee/{employeeId}。"""

    @ns.doc("获取员工个人周排班")
    @login_required
    def get(self, employee_id):
        """返回该员工本周每天排班 + 周统计（契约 4 章）。"""
        from models import Schedule, Employee

        emp = Employee.query.get(employee_id)
        if not emp:
            raise ApiError(ERR_NOT_FOUND, "员工不存在")

        week_start = _parse_date(request.args.get("weekStart")) or _week_start(date.today())
        week_end = week_start + timedelta(days=6)

        rows = (Schedule.query
                .filter(Schedule.employee_id == employee_id)
                .filter(Schedule.work_date.between(week_start, week_end))
                .filter(Schedule.status != "cancelled")
                .all())
        by_date = {r.work_date: r for r in rows}

        shifts = []
        total_hours = 0
        working_days = 0
        for i in range(7):
            d = week_start + timedelta(days=i)
            rec = by_date.get(d)
            if rec:
                working_days += 1
                total_hours += rec.shift.hours if rec.shift else 0
                shifts.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "dayOfWeek": WEEKDAYS[i],
                    "shift": {
                        "name": rec.shift.name if rec.shift else "",
                        "startTime": rec.shift.start_time if rec.shift else "",
                        "endTime": rec.shift.end_time if rec.shift else "",
                    },
                })
            else:
                shifts.append({"date": d.strftime("%Y-%m-%d"), "dayOfWeek": WEEKDAYS[i], "shift": None})

        return success({
            "weekStart": week_start.strftime("%Y-%m-%d"),
            "totalHours": total_hours,
            "workingDays": working_days,
            "shifts": shifts,
        })


# ============================================================
# 月排班日历
# ============================================================
@ns.route("/month")
class MonthCalendar(Resource):
    """GET /schedules/month —— 月排班日历视图。"""

    @ns.doc("获取月排班日历")
    @login_required
    def get(self):
        """查询参数：employeeId（可选）、month（YYYY-MM）。"""
        from models import Schedule
        import calendar

        employee_id = request.args.get("employeeId")
        month_str = request.args.get("month")
        today = date.today()
        if month_str:
            try:
                y, m = map(int, month_str.split("-"))
            except (ValueError, AttributeError):
                raise ApiError(ERR_PARAM, "month 格式应为 YYYY-MM")
        else:
            y, m = today.year, today.month

        first_day = date(y, m, 1)
        last_day = date(y, m, calendar.monthrange(y, m)[1])

        query = (Schedule.query
                 .filter(Schedule.work_date.between(first_day, last_day))
                 .filter(Schedule.status != "cancelled"))
        if employee_id:
            query = query.filter(Schedule.employee_id == employee_id)
        rows = query.all()

        by_date = {}
        total_hours = 0
        for r in rows:
            by_date.setdefault(r.work_date.strftime("%Y-%m-%d"), []).append(r.to_dict())
            total_hours += r.shift.hours if r.shift else 0

        return success({
            "month": f"{y:04d}-{m:02d}",
            "totalHours": total_hours,
            "days": by_date,
        })


# ============================================================
# 分配员工到班次（含冲突检测）
# ============================================================
@ns.route("/assign")
class Assign(Resource):
    """POST /schedules/assign —— 分配员工到班次。"""

    @ns.doc("分配员工到班次")
    @require_permission("shift:assign")
    def post(self):
        """请求体：{ employeeId, shiftId, date }。

        冲突检测（需求 4.3）：
        - 同一员工同一天只能 1 个班次 -> 4001
        - 已离职员工不能排班 -> 4001
        - 当周超过 5 天 -> 返回 warning 字段（不阻断，允许强制确认）
        """
        from models import Schedule, Employee, Shift
        from extensions import db

        body = request.get_json(silent=True) or {}
        employee_id = body.get("employeeId")
        shift_code = body.get("shiftId")
        d = _parse_date(body.get("date"))
        if not employee_id or not shift_code or not d:
            raise ApiError(ERR_PARAM, "employeeId、shiftId、date 均为必填")

        emp = Employee.query.get(employee_id)
        if not emp:
            raise ApiError(ERR_NOT_FOUND, "员工不存在")
        if emp.status == "resigned":
            raise ApiError(ERR_BUSINESS, "已离职员工不能排班")

        shift = Shift.query.filter_by(code=shift_code).first()
        if not shift:
            raise ApiError(ERR_NOT_FOUND, "班次不存在")

        # 冲突 1：同一天已有排班
        existed = (Schedule.query
                   .filter_by(employee_id=employee_id, work_date=d)
                   .filter(Schedule.status != "cancelled")
                   .first())
        if existed:
            raise ApiError(ERR_BUSINESS, "该员工当天已有排班，不能重复安排")

        # 周工时超限警告（不阻断）
        week_start = _week_start(d)
        week_end = week_start + timedelta(days=6)
        week_days = (Schedule.query
                     .filter(Schedule.employee_id == employee_id)
                     .filter(Schedule.work_date.between(week_start, week_end))
                     .filter(Schedule.status != "cancelled")
                     .with_entities(Schedule.work_date).distinct().count())
        warning = None
        if week_days >= 5:
            warning = f"该员工当周已排 {week_days} 天，超过 5 天限制"

        rec = Schedule(employee_id=employee_id, shift_id=shift.id, work_date=d, status="draft")
        db.session.add(rec)
        db.session.commit()

        data = rec.to_dict()
        if warning:
            data["warning"] = warning
        return success(data, "分配成功")


# ============================================================
# 取消排班
# ============================================================
@ns.route("/<string:schedule_id>")
class ScheduleItem(Resource):
    """DELETE /schedules/{scheduleId} —— 取消排班。"""

    @ns.doc("取消排班")
    @require_permission("shift:assign")
    def delete(self, schedule_id):
        """将排班状态置为 cancelled（保留记录）。"""
        from models import Schedule
        from extensions import db

        rec = Schedule.query.get(schedule_id)
        if not rec:
            raise ApiError(ERR_NOT_FOUND, "排班记录不存在")
        rec.status = "cancelled"
        db.session.commit()
        return success(None, "排班已取消")


# ============================================================
# 发布周排班
# ============================================================
@ns.route("/publish")
class Publish(Resource):
    """POST /schedules/publish —— 发布周排班。"""

    @ns.doc("发布周排班")
    @require_permission("shift:publish")
    def post(self):
        """请求体：{ weekStart }。把该周 draft 排班置为 published。"""
        from models import Schedule
        from extensions import db

        body = request.get_json(silent=True) or {}
        week_start = _parse_date(body.get("weekStart"))
        if not week_start:
            raise ApiError(ERR_PARAM, "缺少参数 weekStart")
        week_end = week_start + timedelta(days=6)

        count = (Schedule.query
                 .filter(Schedule.work_date.between(week_start, week_end))
                 .filter(Schedule.status == "draft")
                 .update({"status": "published"}, synchronize_session=False))
        db.session.commit()
        return success({"publishedCount": count}, "排班已发布")


# ============================================================
# 导出排班
# ============================================================
@ns.route("/export")
class Export(Resource):
    """GET /schedules/export —— 导出排班表（CSV/PDF）。"""

    @ns.doc("导出排班表")
    @login_required
    def get(self):
        """查询参数：weekStart, format（csv / pdf）。

        CSV 直接生成；PDF 需要额外渲染库，课程项目暂以 CSV 为主，
        format=pdf 时返回 4001 提示暂不支持（可在 P1 补充）。
        """
        from models import Schedule

        week_start = _parse_date(request.args.get("weekStart")) or _week_start(date.today())
        fmt = (request.args.get("format") or "csv").lower()
        if fmt != "csv":
            raise ApiError(ERR_BUSINESS, f"暂不支持导出格式：{fmt}")

        week_end = week_start + timedelta(days=6)
        rows = (Schedule.query
                .filter(Schedule.work_date.between(week_start, week_end))
                .filter(Schedule.status != "cancelled")
                .order_by(Schedule.work_date, Schedule.shift_id)
                .all())

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["日期", "星期", "员工", "班次", "开始", "结束", "工时"])
        for r in rows:
            writer.writerow([
                r.work_date.strftime("%Y-%m-%d"),
                WEEKDAYS[r.work_date.weekday()],
                r.employee.real_name if r.employee else "",
                r.shift.name if r.shift else "",
                r.shift.start_time if r.shift else "",
                r.shift.end_time if r.shift else "",
                r.shift.hours if r.shift else 0,
            ])

        # 加 BOM 让 Excel 正确识别 UTF-8 中文
        content = "\ufeff" + buf.getvalue()
        filename = f"schedule_{week_start.strftime('%Y-%m-%d')}.csv"
        return Response(
            content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )