# -*- coding: utf-8 -*-
"""
初始化种子数据 —— 供开发/演示使用。

运行方式（在项目根目录）：
    .venv\\Scripts\\python.exe backend\\seed.py

幂等设计：已存在的记录会跳过，可安全重复运行。
填充内容：
- 部门字典
- 员工类型 + 默认时薪（需求 3.2）
- 三种固定班次（需求 4.1）
- 覆盖全部角色的测试账号（密码均为 123456）
- 示例商品库存
"""
import os
import sys

# Windows 控制台默认 GBK，统一用 UTF-8 输出，避免特殊字符报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from datetime import date

from app import create_app
from extensions import db
from models import Employee, User, Department, EmployeeType, Shift, Product


def seed():
    """写入种子数据。"""
    app = create_app()
    with app.app_context():
        # ---------- 部门 ----------
        dept_names = ["门店运营", "人力资源", "仓储物流", "销售部"]
        depts = {}
        for name in dept_names:
            d = Department.query.filter_by(name=name).first()
            if not d:
                d = Department(name=name)
                db.session.add(d)
                db.session.flush()
            depts[name] = d
        db.session.flush()

        # ---------- 员工类型 + 默认时薪（需求 3.2） ----------
        types = [
            ("fulltime", "全职员工", 30.0),
            ("parttime", "兼职员工", 20.0),
            ("temporary", "临时员工", 18.0),
        ]
        for code, name, wage in types:
            if not EmployeeType.query.filter_by(code=code).first():
                db.session.add(EmployeeType(code=code, name=name, default_hourly_wage=wage))
        db.session.flush()

        # ---------- 三种固定班次（需求 4.1） ----------
        shifts = [
            ("morning", "早班", "08:00", "12:00", 4.0, "#409EFF"),
            ("afternoon", "中班", "12:00", "16:00", 4.0, "#67C23A"),
            ("evening", "晚班", "16:00", "20:00", 4.0, "#E6A23C"),
        ]
        for code, name, st, et, hours, color in shifts:
            shift = Shift.query.filter_by(code=code).first()
            if shift and code == "morning":
                # Keep the morning shift aligned with its canonical hours.
                shift.name = name
                shift.start_time = st
                shift.end_time = et
                shift.hours = hours
                shift.color = color
            elif not shift:
                db.session.add(Shift(code=code, name=name, start_time=st,
                                     end_time=et, hours=hours, color=color))
        db.session.flush()

        # ---------- 测试账号（覆盖所有角色，密码统一 123456） ----------
        # (工号, 姓名, 用户名, 角色, 部门, 职位, 时薪)
        demo_users = [
            ("E001", "门店经理", "manager", "manager", "门店运营", "门店经理", 45.0),
            ("E002", "人事专员", "hr01", "hr_officer", "人力资源", "HR 专员", 35.0),
            ("E003", "排班经理", "sm01", "shift_manager", "门店运营", "排班经理", 38.0),
            ("E004", "仓管员", "wh01", "warehouse_worker", "仓储物流", "仓库管理员", 28.0),
            ("E005", "普通员工", "emp01", "employee", "销售部", "销售员", 30.0),
        ]
        for no, real, username, role, dept, position, wage in demo_users:
            if User.query.filter_by(username=username).first():
                continue
            emp = Employee(
                employee_no=no,
                real_name=real,
                employee_type="fulltime",
                department_id=depts[dept].id,
                position=position,
                hourly_wage=wage,
                hire_date=date(2026, 1, 1),
                roles=role,
            )
            db.session.add(emp)
            db.session.flush()
            account = User(username=username, employee_id=emp.id, roles=role)
            account.set_password("123456")
            db.session.add(account)

        # ---------- 示例商品库存 ----------
        products = [
            ("P001", "充电电钻套装", "power-tools", "电动工具", 100, 20, "套"),
            ("P002", "螺丝刀套装", "hand-tools", "手动工具", 8, 15, "套"),
            ("P003", "白色内墙乳胶漆 5L", "paint-supplies", "油漆与涂料", 0, 10, "桶"),
            ("P004", "PVC 水管 2m", "plumbing", "水暖管件", 50, 15, "根"),
            ("P005", "混凝土钻头套装", "power-tool-accessories", "电动工具配件", 6, 10, "套"),
            ("P006", "镀锌木螺丝 50mm", "fasteners", "紧固件", 18, 20, "盒"),
            ("P007", "防护眼镜", "safety-gear", "安全防护", 35, 12, "副"),
            ("P008", "10 英寸活动扳手", "hand-tools", "手动工具", 4, 8, "把"),
        ]
        for sku, name, cat_id, cat_name, qty, min_lvl, unit in products:
            product = Product.query.filter_by(sku=sku).first()
            if product:
                product.name = name
                product.category_id = cat_id
                product.category_name = cat_name
                product.min_stock_level = min_lvl
                product.unit = unit
            else:
                db.session.add(Product(
                    sku=sku, name=name, category_id=cat_id, category_name=cat_name,
                    stock_quantity=qty, min_stock_level=min_lvl, unit=unit,
                ))

        db.session.commit()
        print("种子数据写入完成")
        print("测试账号（密码均为 123456）：")
        for _, _, username, role, _, _, _ in demo_users:
            print(f"  {username:10s} -> {role}")


if __name__ == "__main__":
    seed()
