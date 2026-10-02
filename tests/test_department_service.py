import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.department_service.main import app as dept_app
from services.shared.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(dept_app) as c:
        yield c

def get_admin_headers():
    token = create_access_token({"sub": "admin-1", "email": "admin@company.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_department_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "department-service"

def test_list_departments(client):
    response = client.get("/departments")
    assert response.status_code == 200
    departments = response.json()
    assert len(departments) >= 5
    codes = [d["code"] for d in departments]
    assert "ENG" in codes
    assert "HR" in codes

def test_department_stats(client):
    response = client.get("/departments/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_departments"] >= 5
    assert stats["total_budget"] > 0

def test_create_and_delete_department(client):
    headers = get_admin_headers()
    dept_payload = {
        "name": "Quality Assurance & Testing",
        "code": "QA",
        "budget": 350000.0,
        "description": "Automated regression and performance test engineering",
        "location": "Austin HQ"
    }
    create_res = client.post("/departments", json=dept_payload, headers=headers)
    assert create_res.status_code == 201
    created_dept = create_res.json()
    assert created_dept["code"] == "QA"

    # Delete
    del_res = client.delete(f"/departments/{created_dept['id']}", headers=headers)
    assert del_res.status_code == 200

def test_department_not_found(client):
    res = client.get("/departments/NON-EXISTENT-ID-12345")
    assert res.status_code == 404

def test_create_department_unauthorized_role(client):
    emp_token = create_access_token({"sub": "emp-1", "email": "emp@company.com", "role": "EMPLOYEE"})
    dept_payload = {
        "name": "Unauthorized Department",
        "code": "UNAUTH",
        "budget": 1000.0
    }
    res = client.post("/departments", json=dept_payload, headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 403

