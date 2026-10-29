# -*- coding: utf-8 -*-
"""
接口冒烟测试 —— 端到端验证所有模块是否符合契约文档 v1.0。

运行前提：先启动后端（python backend/app.py）并已执行 seed.py。
运行方式（项目根目录）：
    .venv\\Scripts\\python.exe backend\\test_api.py

只依赖标准库 urllib，不需要额外安装包。
"""
import json
import sys
from urllib import request, error

BASE = "http://localhost:5000/api/v1"

# Windows 控制台 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


PASS = 0
FAIL = 0


def call(method: str, path: str, token: str = None, body: dict = None):
    """发起 HTTP 请求，返回 (status, json_dict)。"""
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def check(name: str, cond: bool, detail: str = ""):
    """断言并打印结果。"""
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def main():
    print("=" * 60)
    print("美体商城员工管理系统 —— 接口冒烟测试")
    print("=" * 60)

    # ---------- 1. 认证 ----------
    print("\n[1] 认证模块")
    st, r = call("POST", "/auth/login", body={"username": "manager", "password": "123456"})
    check("登录成功", st == 200 and r["code"] == 0, str(r))
    token = r["data"]["token"] if st == 200 else None
    check("返回 token", bool(token))
    check("权限非空", len(r["data"]["userInfo"]["permissions"]) > 0)

    st, r = call("POST", "/auth/login", body={"username": "manager", "password": "wrong"})
    check("错误密码返回 3002", r["code"] == 3002, str(r))

    st, r = call("GET", "/auth/me", token=token)
    check("获取当前用户成功", st == 200 and r["data"]["username"] == "manager", str(r))

    st, r = call("GET", "/auth/me")
    check("未带 token 返回 2001", r["code"] == 2001, str(r))

    # ---------- 2. 员工 ----------
    print("\n[2] 员工模块")
    st, r = call("GET", "/employees?page=1&pageSize=10", token=token)
    check("员工列表分页结构", st == 200 and "list" in r["data"] and "total" in r["data"], str(r))
    employees = r["data"]["list"] if st == 200 else []
    check("员工列表非空", len(employees) > 0)
    mgr = next((e for e in employees if e["realName"] == "门店经理"), None)
    check("manager 可见 hourlyWage(敏感字段)", mgr and "hourlyWage" in mgr)

    emp_id = employees[0]["id"] if employees else None
    st, r = call("GET", f"/employees/{emp_id}", token=token)
    check("员工详情成功", st == 200 and r["data"]["id"] == emp_id, str(r))

    # 字段级权限：仓管员不能看 hourlyWage
    st, r = call("POST", "/auth/login", body={"username": "wh01", "password": "123456"})
    wh_token = r["data"]["token"]
    st, r = call("GET", f"/employees/{emp_id}", token=wh_token)
    check("仓管员不可见 hourlyWage", "hourlyWage" not in r["data"], str(r))

    # ---------- 3. 班次 ----------
    print("\n[3] 班次模块")
    st, r = call("GET", "/shifts", token=token)
    check("班次列表有 3 种", st == 200 and len(r["data"]) == 3, str(r))
    shift_codes = [s["code"] for s in r["data"]] if st == 200 else []
    check("含 morning/afternoon/evening", set(shift_codes) == {"morning", "afternoon", "evening"}, str(shift_codes))

    # ---------- 4. 排班 ----------
    print("\n[4] 排班模块")
    st, r = call("GET", "/schedules/week", token=token)
    check("周排班总览结构", st == 200 and "days" in r["data"] and len(r["data"]["days"]) == 7, str(r))

    # 找一个普通员工分配排班
    from urllib.parse import quote
    st, r = call("GET", "/employees?keyword=" + quote("普通员工"), token=token)
    worker_id = r["data"]["list"][0]["id"] if r["data"]["list"] else emp_id

    st, r = call("POST", "/schedules/assign", token=token,
                 body={"employeeId": worker_id, "shiftId": "morning", "date": "2026-10-20"})
    check("分配排班成功", st == 200 and r["code"] == 0, str(r))
    sched_id = r["data"]["id"] if st == 200 else None

    # 冲突：同一员工同一天再次排班 -> 4001
    st, r = call("POST", "/schedules/assign", token=token,
                 body={"employeeId": worker_id, "shiftId": "evening", "date": "2026-10-20"})
    check("同天重复排班返回 4001", r["code"] == 4001, str(r))

    # 取消排班
    if sched_id:
        st, r = call("DELETE", f"/schedules/{sched_id}", token=token)
        check("取消排班成功", st == 200 and r["code"] == 0, str(r))

    # 发布排班
    st, r = call("POST", "/schedules/publish", token=token, body={"weekStart": "2026-10-19"})
    check("发布排班成功", st == 200 and r["code"] == 0, str(r))

    # ---------- 5. 请假 ----------
    print("\n[5] 请假模块")
    st, r = call("POST", "/auth/login", body={"username": "emp01", "password": "123456"})
    emp_token = r["data"]["token"]
    st, r = call("POST", "/leaves", token=emp_token,
                 body={"leaveType": "sick", "startDate": "2026-10-22", "endDate": "2026-10-23", "reason": "test"})
    check("提交请假成功", st == 200 and r["code"] == 0, str(r))
    leave_id = r["data"]["id"] if st == 200 else None

    st, r = call("GET", "/leaves/my", token=emp_token)
    check("我的请假记录", st == 200 and r["data"]["total"] >= 1, str(r))

    if leave_id:
        st, r = call("PUT", f"/leaves/{leave_id}/approve", token=token,
                     body={"status": "approved", "comment": "ok"})
        check("审批请假成功", st == 200 and r["code"] == 0, str(r))

    # ---------- 6. 库存 ----------
    print("\n[6] 库存模块")
    st, r = call("GET", "/inventory", token=wh_token)
    check("库存列表", st == 200 and r["data"]["total"] > 0, str(r))
    products = r["data"]["list"] if st == 200 else []

    st, r = call("GET", "/inventory/low-stock", token=wh_token)
    check("低库存预警", st == 200 and isinstance(r["data"], list), str(r))

    # ---------- 7. 补货（状态流转 + 库存增加） ----------
    print("\n[7] 补货模块")
    prod = products[0] if products else None
    if prod:
        old_qty = prod["stockQuantity"]
        # 需求矩阵 2.2：仓管员无 restock:request 权限，提交应被拒绝(2003)
        st, r = call("POST", "/restock-requests", token=wh_token,
                     body={"productId": prod["id"], "requestedQuantity": 1})
        check("仓管员提交补货被拒绝(2003)", r["code"] == 2003, str(r))
        # 需求矩阵 2.2：补货请求由普通员工创建，仓管员只负责处理
        st, r = call("POST", "/restock-requests", token=emp_token,
                     body={"productId": prod["id"], "requestedQuantity": 5})
        check("员工提交补货申请", st == 200 and r["code"] == 0, str(r))
        req_id = r["data"]["id"] if st == 200 else None

        if req_id:
            # 非法流转：pending 直接到 completed
            st, r = call("PUT", f"/restock-requests/{req_id}/process", token=wh_token,
                         body={"status": "completed"})
            check("非法状态流转返回 4001", r["code"] == 4001, str(r))

            # 合法：pending -> processing
            st, r = call("PUT", f"/restock-requests/{req_id}/process", token=wh_token,
                         body={"status": "processing"})
            check("pending->processing 成功", st == 200 and r["data"]["status"] == "processing", str(r))

            # 合法：processing -> completed（库存增加）
            st, r = call("PUT", f"/restock-requests/{req_id}/process", token=wh_token,
                         body={"status": "completed"})
            check("processing->completed 成功", st == 200 and r["data"]["status"] == "completed", str(r))

            st, r = call("GET", f"/inventory?keyword={prod['sku']}", token=wh_token)
            new_qty = r["data"]["list"][0]["stockQuantity"] if r["data"]["list"] else None
            check("完成后库存增加", new_qty == old_qty + 5, f"old={old_qty}, new={new_qty}")

    # ---------- 8. 统计 ----------
    print("\n[8] 统计模块")
    st, r = call("GET", "/stats/workforce", token=token)
    check("人力统计总览", st == 200 and "totalEmployees" in r["data"], str(r))

    st, r = call("GET", "/stats/inventory", token=token)
    check("库存统计", st == 200 and "totalSku" in r["data"], str(r))

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"测试完成：PASS={PASS}  FAIL={FAIL}")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())