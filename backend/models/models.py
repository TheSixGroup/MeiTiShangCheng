# -*- coding: utf-8 -*-
"""
数据模型定义 —— 对应接口契约文档 v1.0 的所有数据结构。

设计说明：
- 所有主键使用字符串（契约 1.5 节：ID 类型为 string，防止 JS 精度丢失）。
- 时间序列化统一为 "YYYY-MM-DD HH:mm:ss"（契约 1.5 节）。
- 日期序列化统一为 "YYYY-MM-DD"。
- 员工采用软删除（status=resigned），不做物理删除（需求确认文档 3 节）。

每个模型都提供 to_dict() 方法，返回符合契约的 JSON 结构，
资源层直接调用即可，避免各接口重复拼装字段。
"""
import uuid
from datetime import datetime, date

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


# ============================================================
# 公共工具函数
# ============================================================
def gen_id() -> str:
    """生成全局唯一字符串 ID（32 位十六进制）。"""
    return uuid.uuid4().hex


def now() -> datetime:
    """当前时间（服务器本地时间，部署时区应为 UTC+8）。"""
    return datetime.now()


def fmt_dt(dt: datetime) -> str | None:
    """datetime 序列化为 'YYYY-MM-DD HH:mm:ss'（契约 1.5 节）。"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def fmt_date(d: date) -> str | None:
    """date 序列化为 'YYYY-MM-DD'（契约 1.5 节）。"""
    return d.strftime("%Y-%m-%d") if d else None


# ============================================================
# 用户账号（登录用）—— 契约文档 1.4 节认证
# ============================================================
class User(db.Model):
    """登录账号表。

    一个员工对应一个登录账号。角色以逗号分隔字符串存储（roles），
    权限在登录时根据角色动态计算后返回（契约 1.4 节）。
    """

    __tablename__ = "users"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)
    roles = db.Column(db.String(512), nullable=False, default="employee")  # 逗号分隔
    created_at = db.Column(db.DateTime, default=now)

    employee = db.relationship("Employee", backref=db.backref("account", uselist=False))

    # ---------- 密码 ----------
    def set_password(self, raw: str) -> None:
        """设置密码（存储哈希值，绝不存明文）。"""
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        """校验明文密码是否正确。"""
        return check_password_hash(self.password_hash, raw)

    # ---------- 角色 ----------
    def role_list(self) -> list:
        """返回角色列表。"""
        return [r for r in (self.roles or "").split(",") if r]

    def permissions(self) -> list:
        """根据角色计算权限码列表（契约 8.2 节权限码清单）。"""
        return calc_permissions(self.role_list())

    def to_userinfo(self) -> dict:
        """返回契约 1.4 节的 userInfo 结构。"""
        emp = self.employee
        return {
            "id": self.id,
            "username": self.username,
            "realName": emp.real_name if emp else self.username,
            "avatar": "",
            "email": emp.email if emp else "",
            "phone": emp.phone if emp else "",
            "roles": self.role_list(),
            "permissions": self.permissions(),
        }


# ============================================================
# 角色 → 权限映射（契约 8.2 节 权限码清单）
# ============================================================
ROLE_PERMISSIONS = {
    "employee": [
        "shift:view", "leave:apply", "restock:request",
    ],
    "shift_manager": [
        "employee:view",
        "shift:view", "shift:assign", "shift:publish",
        "leave:apply", "restock:request",
    ],
    "hr_officer": [
        "employee:view", "employee:add", "employee:edit", "employee:delete",
        "shift:view", "leave:apply", "leave:approve",
        "restock:request", "stats:view",
    ],
    "warehouse_worker": [
        "shift:view",
        "inventory:view", "inventory:manage",
        "leave:apply",
    ],
    "manager": [
        "employee:view", "employee:add", "employee:edit", "employee:delete",
        "shift:view", "shift:assign", "shift:publish",
        "leave:apply", "leave:approve",
        "inventory:view", "inventory:manage", "stats:view",
    ],
}


def calc_permissions(roles: list) -> list:
    """根据角色列表合并去重后的权限码。"""
    result = []
    for r in roles:
        for p in ROLE_PERMISSIONS.get(r, []):
            if p not in result:
                result.append(p)
    return result


# ============================================================
# 部门 —— 契约 3.1 员工数据结构 departmentId/departmentName
# ============================================================
class Department(db.Model):
    """部门字典表。"""

    __tablename__ = "departments"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    name = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


# ============================================================
# 员工类型 + 时薪 —— 需求文档 3.2 节
# ============================================================
class EmployeeType(db.Model):
    """员工类型字典表，含默认时薪（需求文档 3.2 节）。

    fulltime=全职、parttime=兼职、temporary=临时。
    """

    __tablename__ = "employee_types"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    code = db.Column(db.String(32), unique=True, nullable=False)  # fulltime/parttime/temporary
    name = db.Column(db.String(64), nullable=False)                # 显示名
    default_hourly_wage = db.Column(db.Float, nullable=False, default=0.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "defaultHourlyWage": self.default_hourly_wage,
        }


# ============================================================
# 员工 —— 契约 3.1 节员工数据结构
# ============================================================
class Employee(db.Model):
    """员工表（软删除）。

    status: active / on_leave / resigned（需求文档 3.1）
    employeeType: fulltime / parttime / temporary（需求文档 3.2）
    敏感字段（hourlyWage 等）由资源层根据字段级权限决定是否返回（需求 2.3）。
    """

    __tablename__ = "employees"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    employee_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    real_name = db.Column(db.String(64), nullable=False, index=True)
    gender = db.Column(db.String(8), default="male")  # male/female
    phone = db.Column(db.String(32), default="")
    email = db.Column(db.String(128), default="")
    # 外键 → employee_types.code：把类图中 Employee—EmployeeType 的 N:1 关联真正落到库里。
    # 注意 SQLite 默认不校验外键，需配合 extensions.py 里的 PRAGMA foreign_keys=ON。
    employee_type = db.Column(
        db.String(32), db.ForeignKey("employee_types.code"), default="fulltime"
    )
    department_id = db.Column(db.String(32), db.ForeignKey("departments.id"), nullable=True)
    position = db.Column(db.String(64), default="")
    hourly_wage = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(16), default="active", index=True)
    hire_date = db.Column(db.Date, nullable=True)
    leave_date = db.Column(db.Date, nullable=True)
    sick_leave_days = db.Column(db.Integer, default=10)
    annual_leave_days = db.Column(db.Integer, default=10)
    roles = db.Column(db.String(512), default="employee")  # 逗号分隔
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    department = db.relationship("Department")

    def role_list(self) -> list:
        return [r for r in (self.roles or "").split(",") if r]

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """序列化为契约 3.1 节结构。

        :param include_sensitive: 是否包含敏感字段（hourlyWage 等）。
            需求文档 2.3 节：仅 hr_officer 和 manager 可见。
        """
        data = {
            "id": self.id,
            "employeeNo": self.employee_no,
            "username": self.account.username if self.account else "",
            "realName": self.real_name,
            "gender": self.gender,
            "phone": self.phone,
            "email": self.email,
            "employeeType": self.employee_type,
            "departmentId": self.department_id or "",
            "departmentName": self.department.name if self.department else "",
            "position": self.position,
            "status": self.status,
            "hireDate": fmt_date(self.hire_date),
            "leaveDate": fmt_date(self.leave_date),
            "sickLeaveDays": self.sick_leave_days,
            "annualLeaveDays": self.annual_leave_days,
            "roles": self.role_list(),
            "createdAt": fmt_dt(self.created_at),
            "updatedAt": fmt_dt(self.updated_at),
        }
        if include_sensitive:
            data["hourlyWage"] = self.hourly_wage
        return data


# ============================================================
# 班次定义 —— 契约 4.1 节
# ============================================================
class Shift(db.Model):
    """固定班次定义（早班/中班/晚班），需求文档 4.1 节。"""

    __tablename__ = "shifts"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    code = db.Column(db.String(32), unique=True, nullable=False)  # morning/afternoon/evening
    name = db.Column(db.String(32), nullable=False)
    start_time = db.Column(db.String(8), nullable=False)  # HH:mm
    end_time = db.Column(db.String(8), nullable=False)    # HH:mm
    hours = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(16), default="#409EFF")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "hours": self.hours,
            "color": self.color,
        }


# ============================================================
# 排班记录 —— 契约 4.2 节
# ============================================================
class Schedule(db.Model):
    """排班记录表。

    status: draft / published / cancelled（需求文档 4.2）
    一张表存计划排班；实际打卡另存 attendances 表（需求文档 5）。
    """

    __tablename__ = "schedules"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    shift_id = db.Column(db.String(32), db.ForeignKey("shifts.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(16), default="draft", index=True)
    notes = db.Column(db.String(256), default="")
    created_at = db.Column(db.DateTime, default=now)

    employee = db.relationship("Employee")
    shift = db.relationship("Shift")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employeeId": self.employee_id,
            "employeeName": self.employee.real_name if self.employee else "",
            "shiftId": self.shift.code if self.shift else "",
            "shiftName": self.shift.name if self.shift else "",
            "date": fmt_date(self.work_date),
            "startTime": self.shift.start_time if self.shift else "",
            "endTime": self.shift.end_time if self.shift else "",
            "hours": self.shift.hours if self.shift else 0,
            "status": self.status,
            "notes": self.notes or "",
        }


# ============================================================
# 请假申请 —— 契约 5.1 节
# ============================================================
class Leave(db.Model):
    """请假申请表。

    leaveType: sick / annual / personal（需求文档 5.1）
    status: pending / approved / rejected（需求文档 5.2）
    """

    __tablename__ = "leaves"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    leave_type = db.Column(db.String(16), nullable=False)  # sick/annual/personal
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Integer, default=1)
    reason = db.Column(db.String(256), default="")
    status = db.Column(db.String(16), default="pending", index=True)
    approver_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.String(256), default="")
    created_at = db.Column(db.DateTime, default=now)

    employee = db.relationship("Employee", foreign_keys=[employee_id])
    approver = db.relationship("Employee", foreign_keys=[approver_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employeeId": self.employee_id,
            "employeeName": self.employee.real_name if self.employee else "",
            "leaveType": self.leave_type,
            "startDate": fmt_date(self.start_date),
            "endDate": fmt_date(self.end_date),
            "days": self.days,
            "reason": self.reason or "",
            "status": self.status,
            "approverId": self.approver_id,
            "approverName": self.approver.real_name if self.approver else None,
            "approvedAt": fmt_dt(self.approved_at),
            "createdAt": fmt_dt(self.created_at),
        }


# ============================================================
# 打卡记录 —— 需求文档 5 节（Start Work）
# ============================================================
class Attendance(db.Model):
    """实际打卡记录表（与 schedules 计划排班分开）。"""

    __tablename__ = "attendances"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    schedule_id = db.Column(db.String(32), db.ForeignKey("schedules.id"), nullable=True)
    work_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    employee = db.relationship("Employee")

    def to_dict(self) -> dict:
        hours = None
        if self.start_time and self.end_time:
            hours = round((self.end_time - self.start_time).total_seconds() / 3600, 2)
        return {
            "id": self.id,
            "employeeId": self.employee_id,
            "employeeName": self.employee.real_name if self.employee else "",
            "scheduleId": self.schedule_id,
            "date": fmt_date(self.work_date),
            "startTime": fmt_dt(self.start_time),
            "endTime": fmt_dt(self.end_time),
            "hours": hours,
        }


# ============================================================
# 商品库存 —— 契约 6.1 节
# ============================================================
class Product(db.Model):
    """商品库存表。

    status: normal / low_stock / out_of_stock（需求文档 6.1）
    """

    __tablename__ = "products"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    sku = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    category_id = db.Column(db.String(32), default="")
    category_name = db.Column(db.String(64), default="")
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=10)
    unit = db.Column(db.String(8), default="件")
    last_restocked_at = db.Column(db.DateTime, nullable=True)

    def calc_status(self) -> str:
        """根据库存量计算状态（需求文档 6.1）。"""
        if self.stock_quantity <= 0:
            return "out_of_stock"
        if self.stock_quantity <= self.min_stock_level:
            return "low_stock"
        return "normal"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "categoryId": self.category_id,
            "categoryName": self.category_name,
            "stockQuantity": self.stock_quantity,
            "minStockLevel": self.min_stock_level,
            "unit": self.unit,
            "status": self.calc_status(),
            "lastRestockedAt": fmt_dt(self.last_restocked_at),
        }


# ============================================================
# 补货申请 —— 契约 6.2 节
# ============================================================
class RestockRequest(db.Model):
    """补货申请表。

    status: pending / processing / completed（需求文档 6.2）
    处理流程：员工创建 → 仓管员查看 → 标记处理中 → 备货完成 → 标记已完成 → 库存自动增加。
    """

    __tablename__ = "restock_requests"

    id = db.Column(db.String(32), primary_key=True, default=gen_id)
    product_id = db.Column(db.String(32), db.ForeignKey("products.id"), nullable=False, index=True)
    requested_quantity = db.Column(db.Integer, nullable=False)
    requested_by = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(16), default="pending", index=True)
    processed_by = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    product = db.relationship("Product")
    requester = db.relationship("Employee", foreign_keys=[requested_by])
    processor = db.relationship("Employee", foreign_keys=[processed_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "productId": self.product_id,
            "productName": self.product.name if self.product else "",
            "requestedQuantity": self.requested_quantity,
            "requestedBy": self.requester.real_name if self.requester else "",
            "status": self.status,
            "processedBy": self.processor.real_name if self.processor else None,
            "processedAt": fmt_dt(self.processed_at),
            "createdAt": fmt_dt(self.created_at),
        }