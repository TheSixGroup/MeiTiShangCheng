# Mock 数据

前端开发用的模拟接口数据，后端接口上线前可以用这些 JSON 文件先跑通页面逻辑。

## 文件列表

| 文件名 | 对应接口 | 说明 |
|---|---|---|
| `auth-login.json` | `POST /auth/login` | 登录返回 |
| `employees.json` | `GET /employees` | 员工列表（分页） |
| `employee-types.json` | `GET /employee-types` | 员工类型字典 |
| `departments.json` | `GET /departments` | 部门字典 |
| `shifts.json` | `GET /shifts` | 班次定义 |
| `schedules-week.json` | `GET /schedules` | 周排班数据 |
| `inventory.json` | `GET /inventory` | 库存列表 |
| `restock-requests.json` | `GET /restock-requests` | 补货请求列表 |
| `stats-workforce.json` | `GET /stats/workforce` | 人力统计概览 |

## 使用方式

### 方式 1：直接 fetch JSON 文件

```javascript
// 开发环境用 mock 数据
async function getEmployees() {
  const res = await fetch('/mock/employees.json');
  const data = await res.json();
  return data.data;
}
```

### 方式 2：封装 API 层，统一切换

```javascript
// api.js
const USE_MOCK = true; // 后端接口就绪后改成 false

async function request(url, options = {}) {
  if (USE_MOCK) {
    // 根据 URL 映射到对应的 mock 文件
    const mockMap = {
      '/api/v1/employees': '/mock/employees.json',
      '/api/v1/auth/login': '/mock/auth-login.json',
      // ...
    };
    const mockFile = mockMap[url];
    if (mockFile) {
      const res = await fetch(mockFile);
      return res.json();
    }
  }
  const res = await fetch('/api/v1' + url, options);
  return res.json();
}
```

## 数据格式

所有 mock 数据严格遵循 API 文档的统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

后端接口开发完成后，只需把 `USE_MOCK` 改为 `false` 即可无缝切换到真实接口。
