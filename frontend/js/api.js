/**
 * NexusHR Microservices API Gateway Client
 */
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000/api'
    : '/api';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('token') || '';
        this.currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    }

    setAuth(token, user) {
        this.token = token;
        this.currentUser = user;
        localStorage.setItem('token', token);
        localStorage.setItem('currentUser', JSON.stringify(user));
    }

    clearAuth() {
        this.token = '';
        this.currentUser = null;
        localStorage.removeItem('token');
        localStorage.removeItem('currentUser');
    }

    isAuthenticated() {
        return !!this.token;
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {}),
            ...options.headers
        };

        try {
            const response = await fetch(url, { ...options, headers });
            
            const data = await response.json().catch(() => null);
            if (!response.ok) {
                // On 401 unauthorized (except login endpoint), clear token and show login
                if (response.status === 401 && endpoint !== '/auth/login') {
                    this.clearAuth();
                    if (typeof showLoginScreen === 'function') {
                        showLoginScreen('Session expired or unauthorized. Please sign in again.');
                    }
                }
                const detailMsg = (data && data.detail) || `HTTP error ${response.status}`;
                throw new Error(detailMsg);
            }
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // Auth endpoints
    async login(usernameOrEmail, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username_or_email: usernameOrEmail, password })
        });
    }

    async getMe() {
        return this.request('/auth/me');
    }

    async getUsers() {
        return this.request('/auth/users');
    }

    // Health / Services status
    async getServicesStatus() {
        return this.request('/gateway/services-status');
    }

    // Department endpoints
    async getDepartments() {
        return this.request('/departments');
    }

    async getDepartmentStats() {
        return this.request('/departments/stats');
    }

    async createDepartment(deptData) {
        return this.request('/departments', {
            method: 'POST',
            body: JSON.stringify(deptData)
        });
    }

    async updateDepartment(deptId, deptData) {
        return this.request(`/departments/${deptId}`, {
            method: 'PUT',
            body: JSON.stringify(deptData)
        });
    }

    async deleteDepartment(deptId) {
        return this.request(`/departments/${deptId}`, {
            method: 'DELETE'
        });
    }

    // Employee endpoints
    async getEmployees(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/employees${query ? '?' + query : ''}`);
    }

    async getEmployeeStats() {
        return this.request('/employees/stats');
    }

    async getEmployee(empId) {
        return this.request(`/employees/${empId}`);
    }

    async createEmployee(empData) {
        return this.request('/employees', {
            method: 'POST',
            body: JSON.stringify(empData)
        });
    }

    async updateEmployee(empId, empData) {
        return this.request(`/employees/${empId}`, {
            method: 'PUT',
            body: JSON.stringify(empData)
        });
    }

    async deleteEmployee(empId) {
        return this.request(`/employees/${empId}`, {
            method: 'DELETE'
        });
    }

    // Attendance & Leaves endpoints
    async getAttendanceOverview() {
        return this.request(`/attendance/overview?_t=${Date.now()}`, { cache: 'no-store' });
    }

    async getOnDutyCount() {
        return this.request(`/attendance/on-duty/count?_t=${Date.now()}`, { cache: 'no-store' });
    }

    async getAttendanceRecords(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/attendance${query ? '?' + query : ''}`);
    }

    async checkIn(employeeId, employeeName, notes = '') {
        return this.request('/attendance/check-in', {
            method: 'POST',
            body: JSON.stringify({ employee_id: employeeId, employee_name: employeeName, notes })
        });
    }

    async checkOut(employeeId, notes = '') {
        return this.request('/attendance/check-out', {
            method: 'POST',
            body: JSON.stringify({ employee_id: employeeId, notes })
        });
    }

    async getLeaves(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/leaves${query ? '?' + query : ''}`);
    }

    async applyLeave(leaveData) {
        return this.request('/leaves', {
            method: 'POST',
            body: JSON.stringify(leaveData)
        });
    }

    async reviewLeave(leaveId, reviewData) {
        return this.request(`/leaves/${leaveId}/review`, {
            method: 'PUT',
            body: JSON.stringify(reviewData)
        });
    }

    // Performance Reviews
    async getReviews(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/reviews${query ? '?' + query : ''}`);
    }

    async createReview(reviewData) {
        return this.request('/reviews', {
            method: 'POST',
            body: JSON.stringify(reviewData)
        });
    }

    // Payroll endpoints
    async getPayrollMetrics(period = '2026-09') {
        return this.request(`/payroll/metrics?pay_period=${period}`);
    }

    async getPayslips(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/payroll/payslips${query ? '?' + query : ''}`);
    }

    async runBatchPayroll(period, bonusPercentage = 0.0) {
        return this.request('/payroll/batch-run', {
            method: 'POST',
            body: JSON.stringify({ pay_period: period, bonus_percentage: bonusPercentage })
        });
    }

    async generatePayslip(payslipData) {
        return this.request('/payroll/generate', {
            method: 'POST',
            body: JSON.stringify(payslipData)
        });
    }
}

window.apiClient = new ApiClient();
