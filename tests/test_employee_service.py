import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.employee_service.main import app as emp_app
from services.shared.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(emp_app) as c:
        yield c

def get_admin_headers():
    token = create_access_token({"sub": "admin-1", "email": "admin@company.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_employee_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "employee-service"

def test_list_employees(client):
    res = client.get("/employees")
    assert res.status_code == 200
    employees = res.json()
    assert len(employees) >= 8
    emp_ids = [e["employee_id"] for e in employees]
    assert "EMP-001" in emp_ids
    assert "EMP-004" in emp_ids

def test_employee_stats(client):
    res = client.get("/employees/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_employees"] >= 8
    assert data["active_employees"] >= 6
    assert data["avg_salary"] > 50000

def test_create_and_update_employee(client):
    headers = get_admin_headers()
    payload = {
        "employee_id": "EMP-999",
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser999@company.com",
        "phone": "+1 555-0000",
        "department_id": "ENG",
        "job_title": "Software Test Engineer",
        "role": "EMPLOYEE",
        "salary": 110000.0,
        "status": "ACTIVE",
        "skills": ["pytest", "fastapi"]
    }
    create_res = client.post("/employees", json=payload, headers=headers)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["employee_id"] == "EMP-999"

    # Update
    update_res = client.put("/employees/EMP-999", json={"job_title": "Senior Lead SDET"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["job_title"] == "Senior Lead SDET"

    # Cleanup
    del_res = client.delete("/employees/EMP-999", headers=headers)
    assert del_res.status_code == 200

def test_employee_not_found(client):
    res = client.get("/employees/EMP-NONEXISTENT")
    assert res.status_code == 404

def test_create_employee_forbidden_for_employee_role(client):
    emp_token = create_access_token({"sub": "emp-1", "email": "emp@company.com", "role": "EMPLOYEE"})
    payload = {
        "employee_id": "EMP-FORBIDDEN",
        "first_name": "Unauthorized",
        "last_name": "Creation",
        "email": "unauth@company.com",
        "department_id": "ENG",
        "job_title": "Hacker",
        "role": "EMPLOYEE"
    }
    res = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 403

