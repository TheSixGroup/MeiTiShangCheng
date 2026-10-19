// Role-based access control for admin portal
// Roles: hr, shift_manager, warehouse

const ROLES = {
  HR: 'hr',
  SHIFT_MANAGER: 'shift_manager',
  WAREHOUSE: 'warehouse'
};

// Page access permissions: which roles can access which page
const PAGE_PERMISSIONS = {
  'dashboard.html': ['hr', 'shift_manager', 'warehouse'],
  'employees.html': ['hr', 'shift_manager'],
  'employee-add.html': ['hr'],
  'employee-edit.html': ['hr'],
  'shift-planner.html': ['hr', 'shift_manager'],
  'store-schedule.html': ['hr', 'shift_manager'],
  'stats.html': ['hr', 'shift_manager'],
  'inventory.html': ['hr', 'shift_manager', 'warehouse']
};

// Sidebar menu visibility per role (keyed by page filename)
const MENU_PAGE_MAP = {
  'employees.html': ['hr', 'shift_manager'],
  'employee-edit.html': ['hr'],
  'employee-add.html': ['hr'],
  'shift-planner.html': ['hr', 'shift_manager'],
  'store-schedule.html': ['hr', 'shift_manager'],
  'stats.html': ['hr', 'shift_manager'],
  'inventory.html': ['hr', 'shift_manager', 'warehouse']
};

// Feature-level permissions
const FEATURE_PERMISSIONS = {
  // Employee management features
  'employee.edit': ['hr'],
  'employee.delete': ['hr'],
  'employee.add': ['hr'],
  'employee.view.salary': ['hr'],
  'employee.export': ['hr'],

  // Shift planner features
  'shift.assign': ['shift_manager'],
  'shift.edit': ['shift_manager'],
  'shift.publish': ['shift_manager'],

  // Inventory features
  'inventory.process': ['warehouse'],
  'inventory.complete': ['warehouse'],
  'inventory.edit': ['warehouse'],
  'inventory.reorder': ['warehouse', 'shift_manager']
};

// Auth helpers
function getCurrentRole() {
  return localStorage.getItem('adminRole') || null;
}

function getCurrentUsername() {
  return localStorage.getItem('adminUsername') || null;
}

function isLoggedIn() {
  return getCurrentRole() !== null;
}

function login(username, role) {
  localStorage.setItem('adminUsername', username);
  localStorage.setItem('adminRole', role);
}

function logout() {
  localStorage.removeItem('adminUsername');
  localStorage.removeItem('adminRole');
  window.location.href = 'login.html';
}

// Check if current user has access to a page
function canAccessPage(pageName) {
  const role = getCurrentRole();
  if (!role) return false;
  const allowed = PAGE_PERMISSIONS[pageName] || [];
  return allowed.includes(role);
}

// Check if current user can use a feature
function can(feature) {
  const role = getCurrentRole();
  if (!role) return false;
  const allowed = FEATURE_PERMISSIONS[feature] || [];
  return allowed.includes(role);
}

// Redirect to login if not authenticated or no access
function requireAuth(pageName) {
  if (!isLoggedIn()) {
    window.location.href = 'login.html';
    return false;
  }
  if (pageName && !canAccessPage(pageName)) {
    // Redirect to first allowed page
    const role = getCurrentRole();
    for (const [page, roles] of Object.entries(PAGE_PERMISSIONS)) {
      if (roles.includes(role)) {
        window.location.href = page;
        return false;
      }
    }
    logout();
    return false;
  }
  return true;
}

// Apply sidebar menu visibility based on role
function applySidebarPermissions() {
  const role = getCurrentRole();
  if (!role) return;

  // Hide nav items for pages the role can't access
  document.querySelectorAll('.admin-nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (!href || href.startsWith('#')) return;
    
    // Extract filename from href
    const filename = href.split('/').pop().split('?')[0];
    const allowedRoles = MENU_PAGE_MAP[filename];
    
    if (allowedRoles && !allowedRoles.includes(role)) {
      item.style.display = 'none';
    }
  });

  // Hide section labels if all items under them are hidden
  document.querySelectorAll('.admin-nav-sub-label').forEach(label => {
    let next = label.nextElementSibling;
    let hasVisibleItems = false;
    while (next && !next.classList.contains('admin-nav-sub-label')) {
      if (next.classList.contains('admin-nav-item') && next.style.display !== 'none') {
        hasVisibleItems = true;
        break;
      }
      next = next.nextElementSibling;
    }
    if (!hasVisibleItems) {
      label.style.display = 'none';
    }
  });

  // Update user info in sidebar
  const usernameEl = document.getElementById('userName');
  const roleEl = document.getElementById('userRole');
  if (usernameEl) {
    usernameEl.textContent = getCurrentUsername() || 'Admin';
  }
  if (roleEl) {
    roleEl.textContent = getRoleLabel(role);
  }
}

function getRoleLabel(role) {
  const labels = {
    'hr': 'HR Officer',
    'shift_manager': 'Workflow Manager',
    'warehouse': 'Warehouse Worker'
  };
  return labels[role] || role;
}

// Apply feature permissions on a page
// Hides/disables elements with data-permission attribute
function applyFeaturePermissions() {
  const role = getCurrentRole();
  if (!role) return;

  // Elements with data-permission - hide if not allowed
  document.querySelectorAll('[data-permission]').forEach(el => {
    const feature = el.getAttribute('data-permission');
    if (!can(feature)) {
      if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'SELECT') {
        el.disabled = true;
        el.style.opacity = '0.4';
        el.style.cursor = 'not-allowed';
      } else {
        el.style.display = 'none';
      }
    }
  });

  // Elements with data-hide-if - hide for specific roles
  document.querySelectorAll('[data-hide-if]').forEach(el => {
    const hideRoles = el.getAttribute('data-hide-if').split(',').map(r => r.trim());
    if (hideRoles.includes(role)) {
      el.style.display = 'none';
    }
  });

  // Elements with data-disabled-if - disable for specific roles
  document.querySelectorAll('[data-disabled-if]').forEach(el => {
    const disableRoles = el.getAttribute('data-disabled-if').split(',').map(r => r.trim());
    if (disableRoles.includes(role)) {
      el.disabled = true;
      el.style.opacity = '0.4';
      el.style.cursor = 'not-allowed';
    }
  });

  // Salary columns - hide if not HR
  const salaryColumns = document.querySelectorAll('.salary-column, [data-salary]');
  if (!can('employee.view.salary') && salaryColumns.length > 0) {
    salaryColumns.forEach(el => {
      el.style.display = 'none';
    });
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Don't run on login page
  if (document.body.classList.contains('login-page')) return;

  // Apply permissions
  applySidebarPermissions();
  applyFeaturePermissions();

  // Bind sign out link
  const signOutLinks = document.querySelectorAll('.admin-nav-item');
  signOutLinks.forEach(link => {
    const text = link.querySelector('.admin-nav-item-text');
    if (text && text.textContent.trim() === 'Sign out') {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        logout();
      });
    }
  });

  // Update sidebar user info
  const userNameEl = document.querySelector('.admin-sidebar-user-name');
  const userRoleEl = document.querySelector('.admin-sidebar-user-role');
  if (userNameEl && getCurrentUsername()) {
    userNameEl.textContent = getCurrentUsername().charAt(0).toUpperCase() + getCurrentUsername().slice(1) + ' · Admin';
  }
  if (userRoleEl && getCurrentRole()) {
    userRoleEl.textContent = 'Role: ' + getRoleLabel(getCurrentRole());
  }
});
