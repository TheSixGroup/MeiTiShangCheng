# -*- coding: utf-8 -*-
"""
数据模型包。

向后兼容地导出所有模型类，业务层可直接：
    from models import Employee, Schedule, ...
"""
from models.models import (
    User,
    Department,
    EmployeeType,
    Employee,
    Shift,
    Schedule,
    Leave,
    Attendance,
    Product,
    RestockRequest,
    gen_id,
    now,
)

__all__ = [
    "User",
    "Department",
    "EmployeeType",
    "Employee",
    "Shift",
    "Schedule",
    "Leave",
    "Attendance",
    "Product",
    "RestockRequest",
    "gen_id",
    "now",
]