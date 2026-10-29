# 美体商城员工管理系统 —— 后端（Backend）

第六组

基于 **Flask + Flask-RESTX + SQLAlchemy + JWT** 实现，严格遵循《前后端接口契约文档 v1.0》。

---

## 一、技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.14 | 运行时 |
| Flask | 3.1+ | Web 框架 |
| Flask-RESTX | 1.3+ | RESTful API + Swagger 文档 |
| Flask-SQLAlchemy | 3.1+ | ORM |
| Flask-JWT-Extended | 4.7+ | JWT 认证 |
| SQLite | 内置 | 数据库（零配置） |

---

## 三、协作开发规范

### 分支工作流

本项目采用 **"目录隔离 + 功能分支"** 模式：

- **目录隔离**：前端代码放 `frontend/`，后端代码放 `backend/`，文档放 `docs/`，在同一分支下天然隔离。
- **功能分支**：每个新功能从 `main` 拉独立分支开发，完成后通过 Pull Request 合并回 `main`。

```
main（稳定主分支）
  ↓
feature/xxx（功能分支，每人开发新功能时从 main 拉出）
  ↓
开发完成 → 提 PR → Code Review → 合并回 main
```

### 分支命名规范

| 类型 | 命名示例 | 说明 |
|------|----------|------|
| 功能开发 | `feature/login-page` | 新功能开发 |
| Bug 修复 | `fix/login-error` | 修复问题 |
| 文档更新 | `docs/api-v1.1` | 文档类变更 |
| 重构 | `refactor/auth-module` | 代码重构 |

### 提交信息规范

```
feat:     新功能
fix:      修复 bug
docs:     文档变更
style:    格式调整（不影响代码逻辑）
refactor: 重构（不是新增功能也不是修 bug）
test:     测试相关
chore:    构建/工具等杂项
```

示例：
```
feat(frontend): 对接真实后端 API，登录功能联调完成
fix(backend): 修复排班冲突检测逻辑
docs: 更新 API 接口文档至 v1.1
```

---

## 四、快速开始

### 1. 准备环境（首次）

```bash
# 创建虚拟环境
python -m venv .venv

# 安装依赖（Windows，已配置清华镜像的建议）
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 初始化数据

```bash
.venv\Scripts\python.exe backend\seed.py
```

### 3. 启动服务

```bash
.venv\Scripts\python.exe backend\app.py
```

启动后：
- **API BaseURL**：http://localhost:5000/api/v1
- **Swagger 文档**：http://localhost:5000/api/docs
- **健康检查**：http://localhost:5000/api/v1/health

### 4. 运行接口冒烟测试

```bash
.venv\Scripts\python.exe backend\test_api.py
```

---

## 五、测试账号（密码统一 `123456`）

| 用户名 | 角色 | 说明 |
|--------|------|------|
| `manager` | manager | 门店经理（全部权限） |
| `hr01` | hr_officer | 人事专员 |
| `sm01` | shift_manager | 排班经理 |
| `wh01` | warehouse_worker | 仓管员 |
| `emp01` | employee | 普通员工 |

---

## 六、项目结构

```
backend/
├── app.py                  # 应用入口（应用工厂）
├── config.py               # 配置
├── extensions.py           # 扩展初始化（db / jwt）
├── seed.py                 # 初始化种子数据
├── test_api.py             # 接口冒烟测试
├── data.db                 # SQLite 数据库文件（自动生成）
├── models/
│   ├── __init__.py
│   └── models.py           # 全部数据模型
├── common/
│   ├── __init__.py
│   ├── response.py         # 统一响应结构 / 分页
│   ├── errors.py           # 业务错误码 + 全局异常处理
│   └── auth.py             # JWT 认证 + 权限装饰器
└── resources/              # 各业务模块（按契约章节）
    ├── __init__.py         # 统一注册命名空间
    ├── auth.py             # 认证（契约第 2 章）
    ├── employees.py        # 员工（契约第 3 章）
    ├── shifts.py           # 班次定义（契约 4.1）
    ├── schedules.py        # 排班（契约第 4 章）
    ├── leaves.py           # 请假（契约第 5 章）
    ├── inventory.py        # 库存（契约 6.1）
    ├── restock.py          # 补货（契约 6.2）
    ├── stats.py            # 统计（契约第 7 章）
    └── files.py            # 文件上传（契约 1.8）
```

---

## 七、架构说明

- **分层**：`resources`（接口层）→ `models`（数据层），跨模块能力放 `common`。
- **统一响应**：所有接口返回 `{ code, message, data }`（契约 1.2）。
- **统一错误码**：见 `common/errors.py`，以契约 1.6 节为准。
- **权限**：JWT 携带 user_id，每次请求现查用户；装饰器 `@login_required` / `@require_permission()` 校验。
- **字段级权限**：`hourlyWage` 等敏感字段仅 hr_officer / manager 可见（需求 2.3）。
- **软删除**：员工删除即 `status=resigned`，历史数据保留（需求 3 节）。

---

## 八、关键业务规则实现

| 规则 | 实现位置 | 说明 |
|------|----------|------|
| 排班冲突（同天不可双班） | `schedules.py` | 返回 4001 |
| 周超 5 天警告 | `schedules.py` | 返回 warning 字段，不阻断 |
| 补货状态机 | `restock.py` | pending→processing→completed，非法流转 4001 |
| 补货入库 | `restock.py` | 仅首次 completed 时增库存，防重复 |
| 请假扣减假期 | `leaves.py` | 审批通过才扣 sick/annual |
| 仓管员不可创建补货 | `models.py` ROLE_PERMISSIONS | 需求矩阵 2.2 |

---

## 九、文档冲突处理说明

项目两份文档存在少量不一致，本实现统一**以接口契约文档 v1.0 为准**，并在代码注释中标注：

1. **错误码**：契约 1.6 节比需求文档 1.2 节更完整，采用契约版。
2. **排班冲突错误码**：契约第 4 章写 4001（业务错误），虽需求文档写 3001，但契约 1.6 中 3001=资源不存在，故用 4001。
3. **仓管员补货权限**：契约 8.2 写"所有登录用户"，需求矩阵 2.2 明确仓管员 ❌。
   经确认采用**需求矩阵 2.2**：仓管员不能创建补货请求，仅能处理。

---

## 十、常见问题

**Q: 端口 5000 被占用？**
修改 `backend/app.py` 末尾 `app.run(port=5000)` 的端口即可，前端 baseURL 同步修改。

**Q: 数据库要重置？**
删除 `backend/data.db` 后重新运行 `seed.py`。

**Q: Windows 控制台中文乱码？**
`seed.py` 已设置 UTF-8 输出；如仍有问题，执行 `chcp 65001`。

---

## 十一、后续可扩展（P1/P2）

- 考勤打卡接口（attendance，需求 P1）
- PDF 导出（排班表，当前仅 CSV）
- 审计日志（audit-logs，需求 P2）
- 部门/员工类型字典的独立管理接口
