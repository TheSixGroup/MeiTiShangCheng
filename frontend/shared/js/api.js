// API Client for Meiti Shangcheng
// 后端优先同源：后端已同时托管前端页面（app.py 的 FRONTEND_DIR），
// 所以页面从 5000 端口或 HTTPS 隧道打开时，接口直接走同源，无需写死主机和端口。
// 本地用静态服务器调试（如 Live Server 的 http://192.168.x.x:8080）时，
// 自动回退到「同主机的 5000 端口」，保证前后端分离调试也能用。

const _loc = window.location;
const _servedByBackend = _loc.port === '5000' || _loc.protocol === 'https:';

const API_BASE_URL = _servedByBackend
  ? `${_loc.origin}/api/v1`
  : `http://${_loc.hostname}:5000/api/v1`;

// Get JWT token from localStorage
function getToken() {
  return localStorage.getItem('auth_token') || null;
}

// Set JWT token
function setToken(token) {
  localStorage.setItem('auth_token', token);
}

// Clear token
function clearToken() {
  localStorage.removeItem('auth_token');
}

// Get current user info
function getCurrentUser() {
  const userStr = localStorage.getItem('auth_user');
  return userStr ? JSON.parse(userStr) : null;
}

// Set current user info
function setCurrentUser(user) {
  localStorage.setItem('auth_user', JSON.stringify(user));
}

// Clear user info
function clearCurrentUser() {
  localStorage.removeItem('auth_user');
}

// Unified API request function
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    method: options.method || 'GET',
    headers,
    ...options
  };

  if (options.body && typeof options.body !== 'string') {
    config.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    // Handle auth errors
    if (data.code === 2001 || data.code === 2002) {
      // Token invalid or expired - clear and redirect to login
      clearToken();
      clearCurrentUser();
      // Don't redirect on login page
      if (!window.location.pathname.includes('login.html')) {
        window.location.href = '../admin/login.html';
      }
    }

    return data;
  } catch (error) {
    console.error('API request failed:', error);
    return {
      code: 5000,
      message: '网络请求失败，请检查后端服务是否启动',
      data: null
    };
  }
}

// API methods
const api = {
  // Auth
  login: (username, password) => 
    apiRequest('/auth/login', { method: 'POST', body: { username, password } }),
  
  logout: () => 
    apiRequest('/auth/logout', { method: 'POST' }),
  
  getMe: () => 
    apiRequest('/auth/me'),

  // Employees
  getEmployees: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/employees${query ? '?' + query : ''}`);
  },
  
  getEmployee: (id) => 
    apiRequest(`/employees/${id}`),
  
  createEmployee: (data) => 
    apiRequest('/employees', { method: 'POST', body: data }),
  
  updateEmployee: (id, data) => 
    apiRequest(`/employees/${id}`, { method: 'PUT', body: data }),
  
  deleteEmployee: (id) => 
    apiRequest(`/employees/${id}`, { method: 'DELETE' }),

  // Employee types
  getEmployeeTypes: () => 
    apiRequest('/employee-types'),

  // Departments
  getDepartments: () => 
    apiRequest('/departments'),

  // Shifts
  getShifts: () => 
    apiRequest('/shifts'),

  // Schedules
  getSchedulesWeek: (weekStart) => 
    apiRequest(`/schedules/week?weekStart=${weekStart}`),
  
  assignSchedule: (data) => 
    apiRequest('/schedules/assign', { method: 'POST', body: data }),
  
  unassignSchedule: (id) => 
    apiRequest(`/schedules/${id}`, { method: 'DELETE' }),

  // Leaves
  getLeaves: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/leaves${query ? '?' + query : ''}`);
  },
  
  createLeave: (data) => 
    apiRequest('/leaves', { method: 'POST', body: data }),
  
  approveLeave: (id, status, comment) => 
    apiRequest(`/leaves/${id}/approve`, { method: 'PUT', body: { status, comment } }),

  // Inventory
  getInventory: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/inventory${query ? '?' + query : ''}`);
  },

  // Restock
  getRestockRequests: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/restock-requests${query ? '?' + query : ''}`);
  },
  
  createRestockRequest: (data) => 
    apiRequest('/restock-requests', { method: 'POST', body: data }),
  
  processRestock: (id) => 
    apiRequest(`/restock-requests/${id}/process`, { method: 'PUT' }),
  
  completeRestock: (id) => 
    apiRequest(`/restock-requests/${id}/complete`, { method: 'PUT' }),

  // Stats
  getWorkforceStats: () => 
    apiRequest('/stats/workforce'),
  
  getEmployeeHours: (id, month) => 
    apiRequest(`/stats/employee/${id}/hours?month=${month}`),

  // Health check
  health: () => 
    apiRequest('/health')
};
