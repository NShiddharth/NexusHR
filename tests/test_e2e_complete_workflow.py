"""
End-to-End realistic enterprise workflow test:
1. Login as HR Manager
2. Create Department
3. Create Employee
4. Employee logs in
5. Employee records & views attendance (Clock-in / Clock-out)
6. Employee submits leave request
7. Manager / HR approves leave request
8. Payroll is generated & calculated
9. Employee verifies payslip & salary deductions
"""
import pytest
import sys
import uuid
from pathlib import Path
from datetime import date, timedelta
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.auth_service.main import app as auth_app
from services.department_service.main import app as dept_app
from services.employee_service.main import app as emp_app
from services.attendance_service.main import app as att_app
from services.payroll_service.main import app as payroll_app

@pytest.fixture(scope="module")
def auth_client():
    with TestClient(auth_app) as c:
        yield c

@pytest.fixture(scope="module")
def dept_client():
    with TestClient(dept_app) as c:
        yield c

@pytest.fixture(scope="module")
def emp_client():
    with TestClient(emp_app) as c:
        yield c

@pytest.fixture(scope="module")
def att_client():
    with TestClient(att_app) as c:
        yield c

@pytest.fixture(scope="module")
def payroll_client():
    with TestClient(payroll_app) as c:
        yield c

def test_full_9_step_lifecycle_workflow(
    auth_client,
    dept_client,
    emp_client,
    att_client,
    payroll_client
):
    suffix = str(uuid.uuid4())[:6]
    emp_id = f"EMP-{suffix}"
    dept_code = f"D{suffix[:3].upper()}"
    username = f"usr_{suffix}"
    email = f"user.{suffix}@company.com"

    # ==========================================
    # Step 1: Login as HR Manager
    # ==========================================
    hr_login_res = auth_client.post("/auth/login", json={
        "username_or_email": "hrmanager",
        "password": "hr123"
    })
    assert hr_login_res.status_code == 200, f"HR login failed: {hr_login_res.text}"
    hr_token = hr_login_res.json()["access_token"]
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    assert hr_login_res.json()["user"]["role"] in ["HR_MANAGER", "ADMIN"]

    # ==========================================
    # Step 2: Create Department
    # ==========================================
    dept_payload = {
        "name": f"Artificial Intelligence Lab {suffix}",
        "code": dept_code,
        "budget": 2000000.0,
        "description": "Next-gen deep learning, LLMs and quantum optimization lab.",
        "location": "Boston Lab"
    }
    dept_res = dept_client.post("/departments", json=dept_payload, headers=hr_headers)
    assert dept_res.status_code == 201, f"Create department failed: {dept_res.text}"
    dept_data = dept_res.json()
    assert dept_data["code"] == dept_code

    # ==========================================
    # Step 3: Create Employee under new Department
    # ==========================================
    emp_payload = {
        "employee_id": emp_id,
        "first_name": "Marcus",
        "last_name": "Wright",
        "email": email,
        "phone": "+1 (555) 777-8899",
        "department_id": dept_code,
        "department_name": f"Artificial Intelligence Lab {suffix}",
        "job_title": "Lead Quantum AI Scientist",
        "role": "EMPLOYEE",
        "salary": 170000.0,
        "status": "ACTIVE",
        "skills": ["Quantum Computing", "PyTorch", "FastAPI", "Distributed Algorithms"]
    }
    emp_res = emp_client.post("/employees", json=emp_payload, headers=hr_headers)
    assert emp_res.status_code == 201, f"Create employee failed: {emp_res.text}"
    created_emp = emp_res.json()
    assert created_emp["employee_id"] == emp_id
    assert created_emp["full_name"] == "Marcus Wright"

    # Register user account for this employee in Auth service
    user_reg_res = auth_client.post("/auth/register", json={
        "username": username,
        "email": email,
        "full_name": "Marcus Wright",
        "password": "quantumPass123!",
        "role": "EMPLOYEE",
        "employee_id": emp_id
    })
    assert user_reg_res.status_code == 201

    # ==========================================
    # Step 4: Employee Logs In
    # ==========================================
    emp_login_res = auth_client.post("/auth/login", json={
        "username_or_email": username,
        "password": "quantumPass123!"
    })
    assert emp_login_res.status_code == 200
    emp_token = emp_login_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    assert emp_login_res.json()["user"]["employee_id"] == emp_id

    # ==========================================
    # Step 5: Employee records & views Attendance
    # ==========================================
    # Check-in
    checkin_res = att_client.post("/attendance/check-in", json={
        "employee_id": emp_id,
        "employee_name": "Marcus Wright",
        "notes": "Remote from Boston Lab"
    })
    assert checkin_res.status_code == 200
    assert checkin_res.json()["status"] in ["PRESENT", "LATE"]

    # Check-out
    checkout_res = att_client.post("/attendance/check-out", json={
        "employee_id": emp_id,
        "notes": "Completed daily quantum circuit synthesis"
    })
    assert checkout_res.status_code == 200
    assert checkout_res.json()["check_out"] is not None

    # View employee attendance records
    att_list_res = att_client.get(f"/attendance?employee_id={emp_id}")
    assert att_list_res.status_code == 200
    assert len(att_list_res.json()) >= 1

    # ==========================================
    # Step 6: Employee Submits Leave Request
    # ==========================================
    leave_start = date.today() + timedelta(days=14)
    leave_end = date.today() + timedelta(days=16)
    leave_payload = {
        "employee_id": emp_id,
        "employee_name": "Marcus Wright",
        "leave_type": "ANNUAL",
        "start_date": str(leave_start),
        "end_date": str(leave_end),
        "reason": "Quantum Information Conference Speaker"
    }
    leave_res = att_client.post("/leaves", json=leave_payload)
    assert leave_res.status_code == 201
    leave_data = leave_res.json()
    assert leave_data["status"] == "PENDING"
    assert leave_data["days_count"] == 3
    leave_id = leave_data["id"]

    # ==========================================
    # Step 7: HR / Manager Approves Leave Request
    # ==========================================
    review_res = att_client.put(f"/leaves/{leave_id}/review", json={
        "status": "APPROVED",
        "reviewer_id": "EMP-002",
        "reviewer_name": "Sarah Jenkins",
        "review_notes": "Approved with funding for conference trip."
    }, headers=hr_headers)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # ==========================================
    # Step 8: Payroll is Generated & Calculated
    # ==========================================
    # Configure Salary Structure for Employee
    salary_struct_res = payroll_client.post("/payroll/structures", json={
        "employee_id": emp_id,
        "employee_name": "Marcus Wright",
        "base_annual_salary": 170000.0,
        "housing_allowance": 1100.0,
        "transport_allowance": 350.0,
        "medical_allowance": 250.0,
        "tax_percentage": 22.0,
        "pension_percentage": 5.0,
        "insurance_deduction": 200.0
    }, headers=hr_headers)
    assert salary_struct_res.status_code == 201

    # Generate itemized payslip for pay period 2026-10
    payslip_res = payroll_client.post("/payroll/generate", json={
        "employee_id": emp_id,
        "employee_name": "Marcus Wright",
        "department_id": dept_code,
        "pay_period": "2026-10",
        "bonus": 1500.0,
        "other_deductions": 0.0,
        "payment_method": "DIRECT_DEPOSIT"
    }, headers=hr_headers)
    assert payslip_res.status_code == 201
    payslip_data = payslip_res.json()
    assert payslip_data["employee_id"] == emp_id
    assert payslip_data["gross_salary"] > 0
    assert payslip_data["net_salary"] > 0
    assert payslip_data["tax_deduction"] > 0
    payslip_id = payslip_data["id"]

    # ==========================================
    # Step 9: Employee Views Payslip & Checks Calculation
    # ==========================================
    slip_view_res = payroll_client.get(f"/payroll/payslips/{payslip_id}")
    assert slip_view_res.status_code == 200
    slip = slip_view_res.json()
    assert slip["employee_name"] == "Marcus Wright"
    assert slip["pay_period"] == "2026-10"
    assert slip["status"] == "PAID"
    calculated_net = round(slip["gross_salary"] - slip["total_deductions"], 2)
    assert abs(slip["net_salary"] - calculated_net) < 0.02
