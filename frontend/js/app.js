/**
 * NexusHR Enterprise Frontend Application Logic
 */

let allEmployees = [];
let allDepartments = [];
let eventLogs = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    initNavigation();
    initRoleSwitcher();
    setupDefaultDates();
    
    // Immediately fetch Active On Duty on initial page load (sole source of truth: /api/attendance/on-duty/count)
    refreshActiveOnDuty();
    
    // Check if valid token exists in storage
    if (window.apiClient.isAuthenticated()) {
        try {
            const me = await window.apiClient.getMe();
            updateUserUI(me);
            await refreshAllData();
        } catch (err) {
            // Token expired or invalid, reset and prompt login
            window.apiClient.clearAuth();
            showLoginScreen('Session expired. Please sign in again.');
        }
    } else {
        // Automatically perform demo login as admin for initial load
        try {
            await performLogin('admin', 'admin123', true);
            await refreshAllData();
        } catch (err) {
            showLoginScreen('Please sign in to access your workspace');
        }
    }
    
    // Poll services status every 3.5 seconds
    setInterval(checkMicroservicesHealth, 3500);
});

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '24px';
        container.style.right = '24px';
        container.style.zIndex = '9999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgMap = {
        'success': 'rgba(16, 185, 129, 0.95)',
        'error': 'rgba(239, 68, 68, 0.95)',
        'warning': 'rgba(245, 158, 11, 0.95)',
        'info': 'rgba(99, 102, 241, 0.95)'
    };
    const iconMap = {
        'success': 'fa-circle-check',
        'error': 'fa-circle-exclamation',
        'warning': 'fa-triangle-exclamation',
        'info': 'fa-circle-info'
    };

    toast.style.background = bgMap[type] || bgMap['info'];
    toast.style.color = '#ffffff';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '10px';
    toast.style.fontSize = '13px';
    toast.style.fontWeight = '600';
    toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.3)';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '10px';
    toast.style.animation = 'fadeIn 0.2s ease';
    toast.innerHTML = `<i class="fa-solid ${iconMap[type] || 'fa-info'}"></i> <span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Setup tab navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');

    const meta = {
        'dashboard': { title: 'Microservices Architecture & Overview', sub: 'Real-time status of interconnected backend services and organizational metrics' },
        'employees': { title: 'Employee Directory & Talent Roster', sub: 'Manage employee profiles, job titles, department assignments and compensation' },
        'departments': { title: 'Departments & Organizational Hierarchy', sub: 'Department divisions, managerial leaders and allocated budget metrics' },
        'attendance': { title: 'Time Tracking, Attendance & Leaves', sub: 'Daily clock-in logs, real-time work hours and leave authorization workflow' },
        'payroll': { title: 'Payroll, Allowances & Payslips', sub: 'Automated gross-to-net tax calculations and distributed salary ledger' },
        'events': { title: 'Distributed Event Bus Terminal', sub: 'Real-time inter-service async events broadcasted through the message bus' }
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            navItems.forEach(n => n.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            item.classList.add('active');
            const targetTab = document.getElementById(`tab-${tabId}`);
            if (targetTab) targetTab.classList.add('active');

            if (meta[tabId]) {
                pageTitle.innerText = meta[tabId].title;
                pageSubtitle.innerText = meta[tabId].sub;
            }

            if (tabId === 'dashboard' || tabId === 'overview') loadOverviewStats();
            if (tabId === 'attendance') loadAttendance();
            if (tabId === 'payroll') loadPayroll();
        });
    });
}

// Role Switcher Setup
function initRoleSwitcher() {
    const switcher = document.getElementById('user-role-switcher');
    const passwords = {
        'admin': 'admin123',
        'hrmanager': 'hr123',
        'deptmanager': 'manager123',
        'employee': 'emp123'
    };

    switcher.addEventListener('change', async (e) => {
        const username = e.target.value;
        const password = passwords[username] || 'admin123';
        try {
            await performLogin(username, password);
            showToast(`Switched active identity to ${username.toUpperCase()}`, 'info');
            await refreshAllData();
        } catch (err) {
            showToast(`Failed to switch role: ${err.message}`, 'error');
        }
    });
}

function showLoginScreen(message = '') {
    const errorEl = document.getElementById('login-error-msg');
    if (errorEl) {
        if (message) {
            errorEl.innerText = message;
            errorEl.style.display = 'block';
        } else {
            errorEl.style.display = 'none';
        }
    }
    const modal = document.getElementById('modal-login');
    if (modal) {
        modal.classList.add('active');
    }
}

function handleLogout() {
    window.apiClient.clearAuth();

    // Reset user info in sidebar
    const nameEl = document.getElementById('sidebar-user-name');
    const roleEl = document.getElementById('sidebar-user-role');
    const avatarEl = document.getElementById('sidebar-user-avatar');
    if (nameEl) nameEl.innerText = 'Not Signed In';
    if (roleEl) roleEl.innerText = 'GUEST';
    if (avatarEl) avatarEl.src = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80';

    // Clear sensitive data views
    const empTbody = document.getElementById('employees-table-body');
    if (empTbody) empTbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">Please sign in to view employee directory</td></tr>';
    const deptGrid = document.getElementById('dept-cards-grid');
    if (deptGrid) deptGrid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 24px; color: var(--text-muted);">Please sign in to view departments</div>';
    const attTbody = document.getElementById('attendance-table-body');
    if (attTbody) attTbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 24px; color: var(--text-muted);">Please sign in to view attendance records</td></tr>';
    const payTbody = document.getElementById('payroll-table-body');
    if (payTbody) payTbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">Please sign in to view payroll ledger</td></tr>';

    logEvent('auth.logout', { status: 'logged_out' });
    showToast('Signed out successfully', 'info');
    showLoginScreen('Signed out. Please sign in to continue.');
}

async function fillAndSubmitLogin(username, password) {
    const uInput = document.getElementById('login-username');
    const pInput = document.getElementById('login-password');
    if (uInput) uInput.value = username;
    if (pInput) pInput.value = password;
    await submitLoginForm();
}

async function submitLoginForm(e) {
    if (e && e.preventDefault) e.preventDefault();
    const username = document.getElementById('login-username')?.value.trim();
    const password = document.getElementById('login-password')?.value;
    const errorEl = document.getElementById('login-error-msg');
    const btnSubmit = document.getElementById('btn-login-submit');

    if (!username || !password) {
        if (errorEl) {
            errorEl.innerText = 'Please enter both username/email and password';
            errorEl.style.display = 'block';
        }
        return;
    }

    try {
        if (btnSubmit) {
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';
        }
        await performLogin(username, password);
        const modal = document.getElementById('modal-login');
        if (modal) modal.classList.remove('active');
        if (errorEl) errorEl.style.display = 'none';
        showToast('Authentication successful!', 'success');
        await refreshAllData();
    } catch (err) {
        if (errorEl) {
            errorEl.innerText = err.message || 'Login failed. Invalid credentials.';
            errorEl.style.display = 'block';
        }
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In';
        }
    }
}

async function performLogin(username, password, silent = false) {
    try {
        const res = await window.apiClient.login(username, password);
        window.apiClient.setAuth(res.access_token, res.user);
        updateUserUI(res.user);
        logEvent('auth.login_success', { username, role: res.user.role });
        return res;
    } catch (err) {
        console.error("Login error:", err);
        if (!silent) {
            showToast(`Login failed: ${err.message}`, 'error');
        }
        throw err;
    }
}

function updateUserUI(user) {
    if (!user) return;
    const nameEl = document.getElementById('sidebar-user-name');
    const roleEl = document.getElementById('sidebar-user-role');
    const avatarEl = document.getElementById('sidebar-user-avatar');
    const switcher = document.getElementById('user-role-switcher');

    if (nameEl) nameEl.innerText = user.full_name || user.username || 'User';
    if (roleEl) roleEl.innerText = user.role || 'EMPLOYEE';
    
    const avatarMap = {
        'admin': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
        'hrmanager': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
        'deptmanager': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
        'employee': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80'
    };
    const uname = (user.username || '').toLowerCase();
    if (avatarEl && avatarMap[uname]) {
        avatarEl.src = avatarMap[uname];
    }
    if (switcher && avatarMap[uname]) {
        switcher.value = uname;
    }
}

function setupDefaultDates() {
    const today = new Date().toISOString().split('T')[0];
    const startEl = document.getElementById('leave-start-date');
    const endEl = document.getElementById('leave-end-date');
    if (startEl) startEl.value = today;
    if (endEl) endEl.value = today;
}

// Microservices Cluster Health Check
async function checkMicroservicesHealth() {
    const container = document.getElementById('service-nodes-container');
    if (!container) return;

    try {
        const statusData = await window.apiClient.getServicesStatus();
        
        const allServices = {
            'api-gateway': { status: 'UP', latency_ms: '0.8', port: 8000, description: 'Unified Gateway' },
            ...statusData
        };

        container.innerHTML = Object.entries(allServices).map(([name, info]) => {
            const isUp = info.status === 'UP';
            const latency = info.latency_ms ? `${info.latency_ms}ms` : '--';
            const port = info.port || getServicePort(name);
            
            return `
                <div class="service-node-card">
                    <div class="node-top">
                        <span class="node-name">${name}</span>
                        <div class="node-pulse ${isUp ? '' : 'down'}"></div>
                    </div>
                    <div class="node-meta">
                        <span class="port">:${port}</span>
                        <span style="color: ${isUp ? 'var(--success)' : 'var(--danger)'}; font-weight: 600;">
                            ${isUp ? `${latency}` : 'OFFLINE'}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = `
            <div class="service-node-card" style="grid-column: 1 / -1; text-align: center; color: var(--warning);">
                <i class="fa-solid fa-triangle-exclamation"></i> API Gateway at http://localhost:8000 is reconnecting...
            </div>
        `;
    }
}

function getServicePort(name) {
    const map = {
        'auth-service': 8001,
        'department-service': 8002,
        'employee-service': 8003,
        'attendance-service': 8004,
        'payroll-service': 8005
    };
    return map[name] || 8000;
}

// Refresh all core data across services
async function refreshAllData() {
    await Promise.all([
        checkMicroservicesHealth(),
        loadDepartments(),
        loadEmployees(),
        loadOverviewStats()
    ]);
}

// Active On Duty metric refresh: ONLY source of truth is GET /api/attendance/on-duty/count
async function refreshActiveOnDuty() {
    try {
        const data = await window.apiClient.getOnDutyCount();
        const value = (data && data.on_duty_count !== undefined && data.on_duty_count !== null)
            ? Number(data.on_duty_count)
            : 0;
        console.log("On-duty API:", data ? data.on_duty_count : undefined);
        console.log("Updating Active On Duty:", value);
        const onDutyEl = document.getElementById('stat-active-emp');
        if (onDutyEl) {
            onDutyEl.innerText = !isNaN(value) ? value : 0;
        }
        return value;
    } catch (err) {
        console.error("Error updating Active On Duty from API:", err);
    }
}

async function loadOverviewStats() {
    try {
        const [empStats, deptStats, payrollMetrics] = await Promise.all([
            window.apiClient.getEmployeeStats().catch(() => null),
            window.apiClient.getDepartmentStats().catch(() => null),
            window.apiClient.getPayrollMetrics('2026-09').catch(() => null),
            refreshActiveOnDuty()
        ]);

        if (empStats) {
            const totalEl = document.getElementById('stat-total-emp');
            if (totalEl) totalEl.innerText = empStats.total_employees;
        }

        if (deptStats) {
            const deptEl = document.getElementById('stat-departments');
            if (deptEl) deptEl.innerText = deptStats.active_departments;
        }
        if (payrollMetrics) {
            const payrollEl = document.getElementById('stat-monthly-payroll');
            if (payrollEl) payrollEl.innerText = `$${payrollMetrics.total_net_disbursed.toLocaleString()}`;
        }
    } catch (err) {
        console.error("Error loading overview stats:", err);
    }
}

// Departments
async function loadDepartments() {
    try {
        const depts = await window.apiClient.getDepartments();
        allDepartments = depts || [];
        renderDepartments(allDepartments);
        populateDepartmentDropdowns(allDepartments);
    } catch (err) {
        console.error("Error loading departments:", err);
    }
}

function renderDepartments(departments) {
    const container = document.getElementById('departments-grid-container');
    if (!container) return;

    if (departments.length === 0) {
        container.innerHTML = `<p style="color: var(--text-muted);">No departments found.</p>`;
        return;
    }

    container.innerHTML = departments.map(d => {
        return `
            <div class="dept-card">
                <div class="dept-card-top">
                    <div class="dept-card-title">
                        <h3>${d.name}</h3>
                        <span class="code-tag">[${d.code}] &bull; ${d.location}</span>
                    </div>
                    <span class="badge ${d.is_active ? 'badge-success' : 'badge-warning'}">
                        ${d.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                </div>
                <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.5;">${d.description || 'Core organizational business unit.'}</p>
                
                <div class="dept-budget-bar">
                    <div style="display: flex; justify-content: space-between; font-size: 12px;">
                        <span style="color: var(--text-muted);">Annual Budget</span>
                        <span style="font-weight: 700; color: #818cf8;">$${d.budget.toLocaleString()}</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: ${Math.min(100, (d.budget / 1500000) * 100)}%;"></div>
                    </div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 1px solid var(--border-color); font-size: 12px;">
                    <span style="color: var(--text-muted);"><i class="fa-solid fa-user-tie"></i> Head: <strong>${d.manager_name || 'Assigned Manager'}</strong></span>
                </div>
            </div>
        `;
    }).join('');
}

function populateDepartmentDropdowns(departments) {
    const filterEl = document.getElementById('employee-dept-filter');
    const modalSelect = document.getElementById('new-emp-dept');
    
    if (filterEl) {
        filterEl.innerHTML = `<option value="">All Departments</option>` + 
            departments.map(d => `<option value="${d.code}">${d.name}</option>`).join('');
    }

    if (modalSelect) {
        modalSelect.innerHTML = departments.map(d => `<option value="${d.code}">${d.name}</option>`).join('');
    }
}

// Employees
async function loadEmployees() {
    try {
        const employees = await window.apiClient.getEmployees();
        allEmployees = employees || [];
        renderEmployeesTable(allEmployees);
        populateEmployeeDropdowns(allEmployees);
    } catch (err) {
        console.error("Error loading employees:", err);
    }
}

function renderEmployeesTable(employees) {
    const tbody = document.getElementById('employees-table-body');
    if (!tbody) return;

    if (employees.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No employees found matching criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = employees.map(emp => {
        const avatar = emp.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80';
        const statusBadgeClass = emp.status === 'ACTIVE' ? 'badge-success' : emp.status === 'ON_LEAVE' ? 'badge-warning' : 'badge-danger';

        return `
            <tr>
                <td>
                    <div class="table-user-cell">
                        <img src="${avatar}" alt="${emp.full_name}" class="table-user-avatar">
                        <div>
                            <div class="user-cell-name">${emp.full_name}</div>
                            <div class="user-cell-sub">${emp.email}</div>
                        </div>
                    </div>
                </td>
                <td><span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--info);">${emp.employee_id}</span></td>
                <td><span class="badge badge-purple">${emp.department_name || emp.department_id}</span></td>
                <td><strong>${emp.job_title}</strong></td>
                <td><span class="badge ${statusBadgeClass}">${emp.status}</span></td>
                <td><strong>$${emp.salary.toLocaleString()}</strong></td>
                <td>
                    <span style="color: #fbbf24; font-weight: 700;">
                        <i class="fa-solid fa-star"></i> ${emp.performance_rating}
                    </span>
                </td>
                <td>
                    <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="handleDeleteEmployee('${emp.employee_id}')">
                        <i class="fa-solid fa-trash" style="color: var(--danger);"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function populateEmployeeDropdowns(employees) {
    const punchSelect = document.getElementById('quick-punch-employee');
    const leaveSelect = document.getElementById('leave-emp-select');

    const options = employees.map(e => `<option value="${e.employee_id}">${e.full_name} (${e.employee_id})</option>`).join('');

    if (punchSelect) punchSelect.innerHTML = options;
    if (leaveSelect) leaveSelect.innerHTML = options;
}

function filterEmployees() {
    const query = document.getElementById('employee-search').value.toLowerCase();
    const dept = document.getElementById('employee-dept-filter').value;
    const status = document.getElementById('employee-status-filter').value;

    const filtered = allEmployees.filter(emp => {
        const matchesQuery = !query || 
            emp.full_name.toLowerCase().includes(query) ||
            emp.employee_id.toLowerCase().includes(query) ||
            emp.job_title.toLowerCase().includes(query) ||
            (emp.skills && emp.skills.some(s => s.toLowerCase().includes(query)));

        const matchesDept = !dept || emp.department_id === dept;
        const matchesStatus = !status || emp.status === status;

        return matchesQuery && matchesDept && matchesStatus;
    });

    renderEmployeesTable(filtered);
}

// Attendance & Leaves
async function loadAttendance() {
    try {
        const [records, leaves] = await Promise.all([
            window.apiClient.getAttendanceRecords({ limit: 20 }),
            window.apiClient.getLeaves()
        ]);

        renderAttendanceTable(records || []);
        renderLeavesList(leaves || []);
    } catch (err) {
        console.error("Error loading attendance:", err);
    }
}

function renderAttendanceTable(records) {
    const tbody = document.getElementById('attendance-table-body');
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No attendance records found.</td></tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => {
        const checkInTime = r.check_in ? new Date(r.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
        const checkOutTime = r.check_out ? new Date(r.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
        const statusClass = r.status === 'PRESENT' ? 'badge-success' : r.status === 'LATE' ? 'badge-warning' : 'badge-purple';

        return `
            <tr>
                <td><strong>${r.employee_name || r.employee_id}</strong></td>
                <td>${r.date}</td>
                <td><span style="font-family: 'JetBrains Mono';">${checkInTime}</span></td>
                <td><span style="font-family: 'JetBrains Mono';">${checkOutTime}</span></td>
                <td><strong>${r.total_hours} hrs</strong></td>
                <td><span class="badge ${statusClass}">${r.status}</span></td>
            </tr>
        `;
    }).join('');
}

function renderLeavesList(leaves) {
    const container = document.getElementById('leaves-list-container');
    if (!container) return;

    if (leaves.length === 0) {
        container.innerHTML = `<p style="color: var(--text-muted); font-size: 13px;">No pending leave applications.</p>`;
        return;
    }

    container.innerHTML = leaves.map(l => {
        const statusClass = l.status === 'APPROVED' ? 'badge-success' : l.status === 'REJECTED' ? 'badge-danger' : 'badge-warning';
        const isPending = l.status === 'PENDING';

        return `
            <div style="background: rgba(16, 21, 36, 0.9); border: 1px solid var(--border-color); border-radius: 12px; padding: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong>${l.employee_name || l.employee_id}</strong>
                    <span class="badge ${statusClass}">${l.status}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">
                    ${l.leave_type} &bull; ${l.start_date} to ${l.end_date} (${l.days_count} days)
                </div>
                <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">"${l.reason}"</p>
                ${isPending ? `
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                        <button class="btn btn-success" style="padding: 4px 10px; font-size: 11px;" onclick="handleReviewLeave('${l.id}', 'APPROVED')">Approve</button>
                        <button class="btn btn-danger" style="padding: 4px 10px; font-size: 11px;" onclick="handleReviewLeave('${l.id}', 'REJECTED')">Reject</button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

// Payroll
async function loadPayroll() {
    const period = document.getElementById('payroll-period-select')?.value || '2026-09';
    try {
        const payslips = await window.apiClient.getPayslips({ pay_period: period });
        renderPayrollTable(payslips || []);
    } catch (err) {
        console.error("Error loading payroll:", err);
    }
}

function renderPayrollTable(payslips) {
    const tbody = document.getElementById('payroll-table-body');
    if (!tbody) return;

    if (payslips.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No payslips generated for this period. Click 'Run Batch' above.</td></tr>`;
        return;
    }

    tbody.innerHTML = payslips.map(p => {
        return `
            <tr>
                <td><span style="font-family: 'JetBrains Mono'; color: var(--accent-primary); font-size: 11px;">${p.payslip_number}</span></td>
                <td><strong>${p.employee_name}</strong></td>
                <td>${p.pay_period}</td>
                <td>$${p.basic_salary.toLocaleString()}</td>
                <td>+$${p.allowances.toLocaleString()}</td>
                <td style="color: var(--danger);">-$${p.tax_deduction.toLocaleString()}</td>
                <td><strong style="color: var(--success); font-size: 14px;">$${p.net_salary.toLocaleString()}</strong></td>
                <td><span class="badge badge-success">${p.status}</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="viewPayslipModal('${p.payslip_number}', '${p.employee_name}', ${p.basic_salary}, ${p.allowances}, ${p.gross_salary}, ${p.tax_deduction}, ${p.net_salary}, '${p.payment_method}')">
                        <i class="fa-solid fa-file-invoice"></i> View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function viewPayslipModal(num, name, basic, allowances, gross, tax, net, method) {
    alert(`📄 OFFICIAL PAYSLIP RECEIPT\n\nPayslip Number: ${num}\nEmployee: ${name}\nBasic Salary: $${basic.toLocaleString()}\nAllowances: +$${allowances.toLocaleString()}\nGross Earnings: $${gross.toLocaleString()}\nTax & Benefits Deducted: -$${tax.toLocaleString()}\n--------------------------------------\nNET DISBURSED: $${net.toLocaleString()}\nDisbursement Method: ${method}`);
}

// Form & Action Handlers
async function handleCreateEmployee(e) {
    e.preventDefault();
    const deptSelect = document.getElementById('new-emp-dept');
    const deptName = deptSelect.options[deptSelect.selectedIndex].text;

    const data = {
        first_name: document.getElementById('new-emp-first-name').value,
        last_name: document.getElementById('new-emp-last-name').value,
        employee_id: document.getElementById('new-emp-id').value,
        email: document.getElementById('new-emp-email').value,
        department_id: deptSelect.value,
        department_name: deptName,
        job_title: document.getElementById('new-emp-title').value,
        salary: parseFloat(document.getElementById('new-emp-salary').value),
        skills: document.getElementById('new-emp-skills').value.split(',').map(s => s.trim()).filter(Boolean)
    };

    try {
        const created = await window.apiClient.createEmployee(data);
        closeModal('modal-add-employee');
        logEvent('employee.created', created);
        await refreshAllData();
        showToast(`Employee ${created.full_name} (${created.employee_id}) created!`, 'success');
    } catch (err) {
        showToast(`Failed to create employee: ${err.message}`, 'error');
    }
}

async function handleDeleteEmployee(empId) {
    if (!confirm(`Are you sure you want to delete employee ${empId}?`)) return;
    try {
        await window.apiClient.deleteEmployee(empId);
        logEvent('employee.deleted', { employee_id: empId });
        await refreshAllData();
        showToast(`Employee ${empId} deleted.`, 'success');
    } catch (err) {
        showToast(`Delete failed: ${err.message}`, 'error');
    }
}

async function handleCreateDepartment(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('new-dept-name').value,
        code: document.getElementById('new-dept-code').value.toUpperCase(),
        budget: parseFloat(document.getElementById('new-dept-budget').value),
        description: document.getElementById('new-dept-desc').value
    };

    try {
        const created = await window.apiClient.createDepartment(data);
        closeModal('modal-add-department');
        logEvent('department.created', created);
        await refreshAllData();
        showToast(`Department '${created.name}' created!`, 'success');
    } catch (err) {
        showToast(`Failed to create department: ${err.message}`, 'error');
    }
}

async function handleQuickCheckIn() {
    const select = document.getElementById('quick-punch-employee');
    const empId = select.value;
    const empName = select.options[select.selectedIndex].text.split(' (')[0];

    try {
        const res = await window.apiClient.checkIn(empId, empName);
        logEvent('attendance.check_in', { employee_id: empId, status: res.status });
        showToast(`Clock-in successful for ${empName}! Status: ${res.status}`, 'success');
        
        // Immediately fetch Active On Duty from GET /api/attendance/on-duty/count and update #stat-active-emp
        await refreshActiveOnDuty();
        
        loadAttendance();
        loadOverviewStats();
    } catch (err) {
        const msg = (err.message || '').toLowerCase();
        if (msg.includes('already completed attendance')) {
            showToast(`${empName} has already completed their shift today (checked in & out). Active On Duty is correct.`, 'warning');
        } else if (msg.includes('already checked in')) {
            showToast(`${empName} is currently checked in. Use Check Out to clock them out.`, 'info');
        } else {
            showToast(`Clock-in error: ${err.message}`, 'error');
        }
        // Immediately refresh Active On Duty from GET /api/attendance/on-duty/count
        await refreshActiveOnDuty();
    }
}

async function handleQuickCheckOut() {
    const select = document.getElementById('quick-punch-employee');
    const empId = select.value;
    const empName = select.options[select.selectedIndex].text.split(' (')[0];

    try {
        const res = await window.apiClient.checkOut(empId);
        logEvent('attendance.check_out', { employee_id: empId, total_hours: res.total_hours });
        showToast(`Clock-out logged for ${empName}! Total: ${res.total_hours} hrs`, 'success');
        
        // Immediately fetch Active On Duty from GET /api/attendance/on-duty/count and update #stat-active-emp
        await refreshActiveOnDuty();
        
        loadAttendance();
        loadOverviewStats();
    } catch (err) {
        showToast(`Clock-out error: ${err.message}`, 'error');
        // Immediately refresh Active On Duty from GET /api/attendance/on-duty/count
        await refreshActiveOnDuty();
    }
}

async function handleApplyLeave(e) {
    e.preventDefault();
    const select = document.getElementById('leave-emp-select');
    const empId = select.value;
    const empName = select.options[select.selectedIndex].text.split(' (')[0];

    const data = {
        employee_id: empId,
        employee_name: empName,
        leave_type: document.getElementById('leave-type-select').value,
        start_date: document.getElementById('leave-start-date').value,
        end_date: document.getElementById('leave-end-date').value,
        reason: document.getElementById('leave-reason').value
    };

    try {
        const created = await window.apiClient.applyLeave(data);
        closeModal('modal-apply-leave');
        logEvent('leave.requested', created);
        loadAttendance();
        showToast(`Leave request submitted for ${empName}!`, 'success');
    } catch (err) {
        showToast(`Failed to apply for leave: ${err.message}`, 'error');
    }
}

async function handleReviewLeave(leaveId, status) {
    const reviewer = window.apiClient.currentUser;
    const reviewData = {
        status: status,
        reviewer_id: reviewer ? reviewer.employee_id || 'ADMIN-01' : 'ADMIN-01',
        reviewer_name: reviewer ? reviewer.full_name : 'Supervisor',
        review_notes: `Processed by ${reviewer?.full_name || 'Admin'}`
    };

    try {
        await window.apiClient.reviewLeave(leaveId, reviewData);
        logEvent('leave.reviewed', { leave_id: leaveId, status });
        loadAttendance();
        showToast(`Leave request ${status.toLowerCase()}!`, 'success');
    } catch (err) {
        showToast(`Authorization error: ${err.message}`, 'error');
    }
}

async function handleBatchPayroll() {
    const period = document.getElementById('batch-pay-month')?.value || '2026-10';
    try {
        const res = await window.apiClient.runBatchPayroll(period, 5.0);
        logEvent('payroll.batch_run', res);
        showToast(`Payroll executed! ${res.payslips_generated} slips issued ($${res.total_net_disbursed.toLocaleString()})`, 'success');
        await refreshAllData();
        loadPayroll();
    } catch (err) {
        showToast(`Payroll run error: ${err.message}`, 'error');
    }
}

// Event Bus Terminal Logging
function logEvent(eventType, payload) {
    const terminal = document.getElementById('event-stream-terminal');
    const time = new Date().toLocaleTimeString();
    const logItem = { time, eventType, payload };
    eventLogs.unshift(logItem);

    if (terminal) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = `<span class="terminal-time">[${time}]</span> <span class="terminal-event">&bull; ${eventType}</span> &rarr; <span style="color: #cbd5e1;">${JSON.stringify(payload)}</span>`;
        terminal.prepend(line);
    }
}

function clearEventStream() {
    const terminal = document.getElementById('event-stream-terminal');
    if (terminal) terminal.innerHTML = '';
    eventLogs = [];
    showToast('Terminal stream cleared', 'info');
}

// Modal controls
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}
