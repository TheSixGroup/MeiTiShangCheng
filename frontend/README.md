# 媒体商城员工管理系统 (Meitǐ Shāngchéng)

The six groups software engineering project planning course's work.

基于 Flask + 原生 HTML/CSS/JS 的媒体商城员工排班与库存管理系统。

---

## 📁 项目结构

```
MeiTiShangCheng/
├── frontend/                 # 前端代码（纯 HTML/CSS/JavaScript）
│   ├── admin/                # 管理后台（Website 2）
│   ├── employee/             # 员工自助端（Website 1）
│   ├── shared/               # 共享资源（CSS 变量、组件、权限控制）
│   ├── mock/                 # Mock 数据（前后端并行开发用）
│   └── README.md             # 前端详细文档
├── docs/
│   └── API.md                # 前后端 API 接口文档 v1.1
├── backend/                  # 后端代码（Flask）
├── .gitignore
└── README.md
```

---

## 🏗️ 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | HTML5 + CSS3 + 原生 JavaScript（无框架） |
| 后端 | Python Flask + Flask-RESTX（Swagger） |
| 数据库 | MySQL / SQLite |
| 接口规范 | RESTful API + JSON |

---

## 🖥️ 前端

### 员工自助端（Website 1）- 6 个页面

1. **登录页** — 员工登录
2. **周排班视图** — 查看本周排班
3. **月历视图** — 月度排班日历
4. **工时统计** — 个人工时汇总
5. **个人资料** — 查看/修改个人信息
6. **请假申请** — 提交请假申请

### 管理后台（Website 2）- 8 个页面

1. **登录页** — 管理员登录（HR / 排班经理 / 仓管）
2. **员工概览** — 员工列表、搜索、筛选
3. **新增员工** — 创建员工档案
4. **编辑员工** — 修改员工信息
5. **排班规划器** — 可视化排班，拖拽分配
6. **门店排班总览** — 全店排班查看
7. **人力统计** — 人员结构、工时统计
8. **库存管理** — 库存查询、补货处理

### 角色权限

| 模块 | HR Officer | Workflow Manager | Warehouse Worker |
|---|---|---|---|
| 员工管理 | ✅ 完整权限 | 👁️ 只读（无薪资） | ❌ 不可见 |
| 排班规划 | 👁️ 只读 | ✅ 可编辑 | ❌ 不可见 |
| 门店排班 | 👁️ 只读 | 👁️ 只读 | ❌ 不可见 |
| 人力统计 | ✅ 可看 | ✅ 可看 | ❌ 不可见 |
| 库存管理 | 👁️ 只读 | 👁️ 只读 | ✅ 完整权限 |

---

## 🔌 API 接口

完整接口文档见 [docs/API.md](docs/API.md)

- **基础路径**：`/api/v1`
- **认证方式**：Token 认证
- **统一响应格式**：`{ code, message, data }`
- **错误码**：见 API 文档第 2 节

### 模块概览

| 模块 | 接口数 | 说明 |
|---|---|---|
| 认证 | 3 | 登录、获取当前用户、登出 |
| 员工管理 | 5 | CRUD + 分页（含字段级权限） |
| 员工类型 | 1 | 角色字典 |
| 部门管理 | 1 | 部门字典 |
| 班次定义 | 1 | 班次配置 |
| 排班管理 | 4 | 周/月排班、分配、取消 |
| 请假管理 | 3 | 申请、列表、审批 |
| 库存管理 | 3 | 列表、详情、调整 |
| 补货请求 | 4 | 创建、列表、处理、完成 |
| 数据导出 | 3 | 员工、排班、工时导出 |
| 工时统计 | 2 | 月度工时、人力概览 |
| 健康检查 | 1 | /health |

---

## 🚀 本地运行

### 前端预览

```bash
cd frontend
python -m http.server 8080
```

然后访问 `http://localhost:8080/`

- 员工端入口：`employee/login.html`
- 管理端入口：`admin/login.html`

### 后端运行（待实现）

```bash
cd backend
pip install -r requirements.txt
python app.py
```

---

## 👥 团队成员

| 角色 | 成员 | 负责模块 |
|---|---|---|
| 前端 | lyfeee-e | 页面开发、Mock 数据 |
| 后端 | Rongyan-hash | Flask API、数据库 |
| 文档 | 2lzr2 | API 接口文档 |
| 产品 | Jane.c416 | Mock 数据、需求确认 |
| 项目管理 | sunrq0312 | 项目规划、README |

---

## 📝 开发进度

- [x] 前端页面开发（14 页）
- [x] 前端角色权限控制
- [x] API 接口文档 v1.1
- [x] Mock 数据
- [ ] 后端 Flask 骨架
- [ ] 数据库设计
- [ ] 后端 API 实现
- [ ] 前后端联调
- [ ] 测试与部署

---

## 📄 许可证

课程项目，仅供学习使用。
