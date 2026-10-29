# API 接口文档 v1.1

> 媒体商城员工管理系统前后端对接规范
> 最后更新：2026-10-19

---

## 目录

1. [通用约定](#1-通用约定)
2. [错误码](#2-错误码)
3. [认证相关](#3-认证相关)
4. [员工管理](#4-员工管理)
5. [员工类型](#5-员工类型)
6. [部门管理](#6-部门管理)
7. [班次定义](#7-班次定义)
8. [排班管理](#8-排班管理)
9. [请假管理](#9-请假管理)
10. [库存管理](#10-库存管理)
11. [补货请求](#11-补货请求)
12. [数据导出](#12-数据导出)
13. [工时统计](#13-工时统计)
14. [健康检查](#14-健康检查)

---

## 1. 通用约定

### Base URL

```
http://localhost:5000/api/v1
```

### 认证方式

使用 Token 认证（JWT 或 Session，后端实现），登录成功后返回 token，后续请求在 Header 中携带：

```
Authorization: Bearer <token>
```

### 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| code | number | 状态码，0 表示成功，其他见错误码 |
| message | string | 描述信息 |
| data | object/array/null | 响应数据，失败时可能为 null |

### 分页参数

列表接口统一分页参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | number | 否 | 1 | 页码，从 1 开始 |
| pageSize | number | 否 | 10 | 每页条数 |

分页响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "pageSize": 10,
    "totalPages": 10
  }
}
```

### 权限说明

接口权限基于角色，在接口描述中标注所需权限。

角色列表：
- `employee` — 普通员工
- `hr_officer` — HR 专员
- `shift_manager` — 排班经理
- `warehouse_worker` — 仓管员
- `manager` — 店长

---

## 2. 错误码

| code | HTTP 状态码 | 说明 |
|---|---|---|
| 0 | 200 | 成功 |
| 1001 | 400 | 参数校验错误 |
| 1002 | 400 | 请求格式错误 |
| 2001 | 401 | 未登录 / Token 无效 |
| 2002 | 401 | Token 已过期 |
| 2003 | 403 | 无权限访问 |
| 3001 | 409 | 资源冲突（排班冲突、编号重复等） |
| 3002 | 400 | 用户名或密码错误 |
| 4001 | 400 | 业务逻辑错误 |
| 4004 | 404 | 资源不存在 |
| 5000 | 500 | 服务器内部错误 |

### 错误响应示例

```json
{
  "code": 2001,
  "message": "未登录或登录已过期",
  "data": null
}
```

---

## 3. 认证相关

### 3.1 登录

```
POST /auth/login
```

**权限**：公开

**请求体**：

```json
{
  "email": "henriette@meiti-sc.com",
  "password": "123456"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| email | string | 是 | 邮箱或员工编号 |
| password | string | 是 | 密码 |

**响应 data**：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1001,
    "name": "Henriette",
    "email": "henriette@meiti-sc.com",
    "role": "hr_officer",
    "department": "HR Department",
    "store": "Zhengzhou flagship",
    "avatar": null
  }
}
```

### 3.2 获取当前用户信息

```
GET /auth/me
```

**权限**：已登录用户

**响应 data**：同登录返回的 user 对象

### 3.3 登出

```
POST /auth/logout
```

**权限**：已登录用户

**响应 data**：`null`

---

## 4. 员工管理

### 4.1 员工列表（分页）

```
GET /employees
```

**权限**：`hr_officer`、`shift_manager`、`manager`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页条数，默认 10 |
| keyword | string | 否 | 搜索关键词（姓名/编号/邮箱） |
| role | string | 否 | 按角色筛选 |
| departmentId | number | 否 | 按部门筛选 |
| status | string | 否 | active / inactive / pending_removal |

**响应 data**：分页结构，list 中每项为员工对象。

> ⚠️ **字段级权限**：`shift_manager` 请求时，不返回 `hourlyWage` 字段。

**员工对象（hr_officer / manager 可见字段）**：

```json
{
  "id": 1042,
  "employeeNo": "MS-1042",
  "name": "Li Wei",
  "email": "liwei@meiti-sc.com",
  "phone": "13800138000",
  "role": "sales_associate",
  "roleLabel": "Sales Associate",
  "departmentId": 1,
  "department": "Sales",
  "hourlyWage": 26.00,
  "contractHours": 38,
  "status": "active",
  "hireDate": "2025-03-15",
  "avatar": null,
  "createdAt": "2025-03-15T09:00:00Z",
  "updatedAt": "2026-09-20T14:30:00Z"
}
```

### 4.2 员工详情

```
GET /employees/{id}
```

**权限**：`hr_officer`、`shift_manager`、`manager`

> 员工本人也可以查看自己的信息，但字段可能受限（P0 阶段不返回报薪）。

**路径参数**：

| 参数 | 类型 | 说明 |
|---|---|---|
| id | number | 员工 ID |

**响应 data**：员工对象

### 4.3 新增员工

```
POST /employees
```

**权限**：`hr_officer`、`manager`

**请求体**：

```json
{
  "employeeNo": "MS-1051",
  "name": "Zhang San",
  "email": "zhangsan@meiti-sc.com",
  "phone": "13900139000",
  "role": "sales_associate",
  "departmentId": 1,
  "hourlyWage": 26.00,
  "contractHours": 38,
  "hireDate": "2026-10-01"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| employeeNo | string | 是 | 员工编号，唯一 |
| name | string | 是 | 姓名 |
| email | string | 是 | 邮箱 |
| phone | string | 否 | 电话 |
| role | string | 是 | 角色编码 |
| departmentId | number | 是 | 部门 ID |
| hourlyWage | number | 是 | 时薪 |
| contractHours | number | 是 | 合同工时（每周） |
| hireDate | string | 是 | 入职日期（YYYY-MM-DD） |

**响应 data**：创建后的员工对象

**可能的错误码**：
- `3001` — 员工编号或邮箱已存在

### 4.4 更新员工

```
PUT /employees/{id}
```

**权限**：`hr_officer`、`manager`

**请求体**：同新增（字段均为可选，只传要更新的字段）

**响应 data**：更新后的员工对象

**可能的错误码**：
- `4004` — 员工不存在
- `3001` — 编号或邮箱冲突

### 4.5 删除员工（软删除）

```
DELETE /employees/{id}
```

**权限**：`hr_officer`、`manager`

**效果**：员工状态变为 `pending_removal`（待离职），确认后变为 `inactive`。

> 具体是直接软删还是走确认流程，后端根据需求实现。P0 阶段建议直接软删除（状态变 inactive）。

**响应 data**：`null`

**可能的错误码**：
- `4004` — 员工不存在

---

## 5. 员工类型

### 5.1 员工类型列表

```
GET /employee-types
```

**权限**：`hr_officer`、`manager`（新增/编辑员工表单用）

**响应 data**：

```json
[
  {
    "id": 1,
    "code": "sales_associate",
    "name": "Sales Associate",
    "defaultHourlyWage": 26.00,
    "description": "店面销售"
  },
  {
    "id": 2,
    "code": "warehouse_employee",
    "name": "Warehouse Employee",
    "defaultHourlyWage": 28.00,
    "description": "仓库员工"
  }
]
```

> 用途：新增员工表单下拉框选择角色时，可联动显示默认时薪。

---

## 6. 部门管理

### 6.1 部门列表

```
GET /departments
```

**权限**：已登录用户（员工筛选下拉用）

**响应 data**：

```json
[
  {
    "id": 1,
    "name": "Sales",
    "code": "sales",
    "manager": null,
    "employeeCount": 12
  },
  {
    "id": 2,
    "name": "Warehouse",
    "code": "warehouse",
    "manager": null,
    "employeeCount": 4
  },
  {
    "id": 3,
    "name": "HR",
    "code": "hr",
    "manager": null,
    "employeeCount": 2
  }
]
```

---

## 7. 班次定义

### 7.1 班次定义列表

```
GET /shifts
```

**权限**：已登录用户

**响应 data**：

```json
[
  {
    "id": 1,
    "code": "morning",
    "name": "Morning Shift",
    "startTime": "08:00",
    "endTime": "16:00",
    "duration": 8,
    "color": "#2D6DB5",
    "description": "早班"
  },
  {
    "id": 2,
    "code": "afternoon",
    "name": "Afternoon Shift",
    "startTime": "12:00",
    "endTime": "20:00",
    "duration": 8,
    "color": "#D49000",
    "description": "午班"
  },
  {
    "id": 3,
    "code": "evening",
    "name": "Evening Shift",
    "startTime": "16:00",
    "endTime": "22:00",
    "duration": 6,
    "color": "#6B3FA0",
    "description": "晚班"
  }
]
```

---

## 8. 排班管理

### 8.1 周排班列表

```
GET /schedules
```

**权限**：`hr_officer`、`shift_manager`、`manager`（管理端）；`employee`（员工端，只能看自己的）

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| weekStart | string | 是 | 周起始日期（周一），格式 YYYY-MM-DD |
| storeId | number | 否 | 门店 ID（管理端） |
| employeeId | number | 否 | 指定员工 ID（管理端筛选） |
| shiftId | number | 否 | 按班次筛选 |

**响应 data**：

```json
{
  "weekStart": "2026-10-12",
  "weekEnd": "2026-10-18",
  "days": [
    {
      "date": "2026-10-12",
      "dayOfWeek": 1,
      "shifts": [
        {
          "id": 5001,
          "shiftId": 1,
          "shiftCode": "morning",
          "shiftName": "Morning Shift",
          "startTime": "08:00",
          "endTime": "16:00",
          "color": "#2D6DB5",
          "employees": [
            {
              "id": 1042,
              "name": "Li Wei",
              "role": "sales_associate",
              "avatar": null
            }
          ],
          "requiredCount": 3,
          "assignedCount": 1
        }
      ]
    }
  ]
}
```

### 8.2 分配员工到班次

```
POST /schedules/assign
```

**权限**：`shift_manager`、`manager`

**请求体**：

```json
{
  "date": "2026-10-12",
  "shiftId": 1,
  "employeeId": 1042
}
```

**响应 data**：创建后的排班记录

**可能的错误码**：
- `3001` — 该员工当天已有排班冲突
- `4004` — 员工或班次不存在

### 8.3 取消班次分配

```
DELETE /schedules/{scheduleId}/employee/{employeeId}
```

**权限**：`shift_manager`、`manager`

**响应 data**：`null`

### 8.4 月排班（员工端日历视图）

```
GET /schedules/month
```

**权限**：`employee`（看自己的）；`shift_manager`、`hr_officer`、`manager`（可看全员）

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| month | string | 是 | 月份，格式 YYYY-MM |
| employeeId | number | 否 | 员工 ID（管理端指定，员工端默认自己） |

**响应 data**：

```json
{
  "month": "2026-10",
  "days": [
    {
      "date": "2026-10-01",
      "hasShift": true,
      "shifts": [
        {
          "shiftCode": "morning",
          "startTime": "08:00",
          "endTime": "16:00",
          "color": "#2D6DB5"
        }
      ],
      "hours": 8
    }
  ],
  "totalHours": 168
}
```

---

## 9. 请假管理

### 9.1 请假申请列表

```
GET /leaves
```

**权限**：
- `employee` — 只能看自己的
- `hr_officer`、`shift_manager`、`manager` — 可看所有待审批的

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status | string | 否 | pending / approved / rejected |
| page | number | 否 | 页码 |
| pageSize | number | 否 | 每页条数 |

### 9.2 提交请假申请

```
POST /leaves
```

**权限**：已登录用户

**请求体**：

```json
{
  "type": "annual",
  "startDate": "2026-10-20",
  "endDate": "2026-10-22",
  "reason": "个人事务",
  "document": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | string | 是 | annual（年假）/ sick（病假）/ personal（事假） |
| startDate | string | 是 | 开始日期 |
| endDate | string | 是 | 结束日期 |
| reason | string | 否 | 请假原因 |
| document | string | 否 | 附件（病假条等） |

**响应 data**：创建后的请假记录

### 9.3 请假审批

```
PUT /leaves/{id}/approve
```

**权限**：`leave:approve`（`hr_officer`、`manager`）

**请求体**：

```json
{
  "status": "approved",
  "comment": "同意，请安排好工作交接"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status | string | 是 | `approved` 或 `rejected` |
| comment | string | 否 | 审批意见 |

**响应 data**：更新后的请假记录

**可能的错误码**：
- `4004` — 请假记录不存在
- `4001` — 状态不是 pending，不能审批

---

## 10. 库存管理

### 10.1 库存列表

```
GET /inventory
```

**权限**：已登录用户

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 搜索关键词（商品名称/SKU） |
| category | string | 否 | 分类 |
| status | string | 否 | in_stock / low_stock / out_of_stock |
| page | number | 否 | 页码 |
| pageSize | number | 否 | 每页条数 |

**响应 data**：分页结构

**库存记录对象**：

```json
{
  "id": 2001,
  "sku": "PRD-001",
  "name": "Media Player Pro",
  "category": "Electronics",
  "quantity": 45,
  "minStock": 20,
  "unit": "pcs",
  "status": "in_stock",
  "lastUpdated": "2026-10-15T10:30:00Z"
}
```

### 10.2 库存详情

```
GET /inventory/{id}
```

**权限**：已登录用户

### 10.3 调整库存

```
PUT /inventory/{id}/adjust
```

**权限**：`warehouse_worker`、`manager`

**请求体**：

```json
{
  "quantity": 10,
  "type": "add",
  "reason": "补货入库",
  "restockRequestId": 3001
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| quantity | number | 是 | 数量（正数） |
| type | string | 是 | `add`（入库）/ `reduce`（出库） |
| reason | string | 否 | 调整原因 |
| restockRequestId | number | 否 | 关联的补货单 ID |

---

## 11. 补货请求

### 11.1 补货请求列表

```
GET /restock-requests
```

**权限**：已登录用户

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| status | string | 否 | pending / processing / completed |
| page | number | 否 | 页码 |
| pageSize | number | 否 | 每页条数 |

**响应 data**：分页结构

**补货请求对象**：

```json
{
  "id": 3001,
  "inventoryId": 2001,
  "inventoryName": "Media Player Pro",
  "sku": "PRD-001",
  "quantity": 50,
  "status": "pending",
  "requesterId": 1042,
  "requesterName": "Li Wei",
  "reason": "库存低于最低值",
  "createdAt": "2026-10-15T09:00:00Z",
  "processedAt": null,
  "processedBy": null,
  "completedAt": null
}
```

### 11.2 创建补货请求

```
POST /restock-requests
```

**权限**：`employee`、`shift_manager`、`hr_officer`、`manager`
（门店侧任何人都可以发起，`warehouse_worker` 不能创建，只能处理）

**请求体**：

```json
{
  "inventoryId": 2001,
  "quantity": 50,
  "reason": "库存低于最低值"
}
```

### 11.3 标记处理中

```
PUT /restock-requests/{id}/process
```

**权限**：`warehouse_worker`、`manager`

**效果**：状态从 `pending` → `processing`

**响应 data**：更新后的补货请求

**可能的错误码**：
- `4001` — 状态不是 pending，不能标记处理中

### 11.4 标记已完成

```
PUT /restock-requests/{id}/complete
```

**权限**：`warehouse_worker`、`manager`

**效果**：状态从 `processing` → `completed`，并自动增加对应商品的库存数量

**响应 data**：更新后的补货请求

**可能的错误码**：
- `4001` — 状态不是 processing，不能完成

---

## 12. 数据导出

所有导出接口返回对应格式的文件流（Content-Type 根据格式不同）。

### 12.1 员工列表导出

```
GET /employees/export?format=csv
```

**权限**：`hr_officer`、`manager`

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| format | string | 否 | csv | 导出格式：`csv` |
| keyword | string | 否 | | 同列表筛选 |
| role | string | 否 | | 同列表筛选 |

> XLSX 格式 P0 不做。

### 12.2 排班导出

```
GET /schedules/export?weekStart=2026-10-13&format=csv
```

**权限**：`hr_officer`、`shift_manager`、`manager`

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| weekStart | string | 是 | 周起始日期 |
| format | string | 否 | 导出格式：`csv` / `pdf`，默认 csv |

### 12.3 员工工时导出

```
GET /stats/employee/{id}/hours/export?month=2026-10&format=csv
```

**权限**：`hr_officer`、`manager`；员工本人可导出自己的

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| month | string | 是 | 月份，格式 YYYY-MM |
| format | string | 否 | 导出格式：`csv`，默认 csv |

---

## 13. 工时统计

### 13.1 员工月度工时

```
GET /stats/employee/{id}/hours
```

**权限**：`hr_officer`、`manager`；员工本人可看自己的

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| month | string | 是 | 月份，格式 YYYY-MM |

**响应 data**：

```json
{
  "employeeId": 1042,
  "employeeName": "Li Wei",
  "month": "2026-10",
  "totalHours": 168,
  "contractHours": 152,
  "overtimeHours": 16,
  "leaveHours": 8,
  "shiftCount": 22,
  "dailyBreakdown": [
    {
      "date": "2026-10-01",
      "hours": 8,
      "shiftType": "morning"
    }
  ]
}
```

### 13.2 人力统计概览

```
GET /stats/workforce
```

**权限**：`hr_officer`、`shift_manager`、`manager`

**响应 data**：

```json
{
  "totalEmployees": 24,
  "activeEmployees": 22,
  "newThisMonth": 3,
  "departuresThisMonth": 1,
  "byRole": [
    { "role": "sales_associate", "count": 12, "percentage": 50.0 }
  ],
  "byDepartment": [
    { "department": "Sales", "count": 12, "percentage": 50.0 }
  ],
  "avgHourlyWage": 27.50,
  "totalWeeklyHours": 760
}
```

---

## 14. 健康检查

### 14.1 健康检查

```
GET /health
```

**权限**：公开

**响应 data**：

```json
{
  "status": "ok",
  "timestamp": "2026-10-18T12:00:00Z",
  "version": "1.0.0"
}
```

---

## 修订记录

| 版本 | 日期 | 修订内容 |
|---|---|---|
| v1.1 | 2026-10-19 | 1. 统一错误码体系<br>2. 补充请假审批接口路径<br>3. 补充员工列表/工时导出接口<br>4. 明确补货请求权限与 process/complete 接口<br>5. 明确字段级权限规则（hourlyWage）<br>6. 新增班次定义、员工类型、部门字典接口 |
| v1.0 | 2026-10-13 | 初始版本 |
