
import pytest
import sys
import uuid
from pathlib import Path
from datetime import date, timedelta
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.attendance_service.main import app as att_app
from services.shared.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(att_app) as c:
        yield c

def get_admin_headers():
    token = create_access_token({"sub": "admin-1", "email": "admin@company.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_attendance_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "attendance-service"

def test_attendance_overview(client):
    res = client.get("/attendance/overview")
    assert res.status_code == 200
    data = res.json()
    assert "today_present" in data
    assert "pending_leaves" in data
    assert "today_on_duty" in data

def test_leave_application_and_approval(client):
    headers = get_admin_headers()
    unique_emp_id = f"EMP-ATT-{str(uuid.uuid4())[:4]}"
    leave_payload = {
        "employee_id": unique_emp_id,
        "employee_name": "Test Att Employee",
        "leave_type": "ANNUAL",
        "start_date": str(date.today() + timedelta(days=20)),
        "end_date": str(date.today() + timedelta(days=22)),
        "reason": "Test personal leave day"
    }
    apply_res = client.post("/leaves", json=leave_payload)
    assert apply_res.status_code == 201
    leave_id = apply_res.json()["id"]
    assert apply_res.json()["status"] == "PENDING"

    # Review / Approve
    review_payload = {
        "status": "APPROVED",
        "reviewer_id": "EMP-002",
        "reviewer_name": "Sarah Jenkins",
        "review_notes": "Approved for testing"
    }
    review_res = client.put(f"/leaves/{leave_id}/review", json=review_payload, headers=headers)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

def test_leave_review_not_found(client):
    headers = get_admin_headers()
    res = client.put("/leaves/NON-EXISTENT-LEAVE-ID/review", json={"status": "APPROVED", "reviewer_id": "EMP-001", "reviewer_name": "Admin"}, headers=headers)
    assert res.status_code == 404

def test_clock_in_and_clock_out(client):
    unique_emp_id = f"EMP-CLOCK-{str(uuid.uuid4())[:4]}"
    in_res = client.post("/attendance/check-in", json={
        "employee_id": unique_emp_id,
        "employee_name": "Clockin Tester",
        "notes": "Arrived at office"
    })
    assert in_res.status_code == 200
    assert in_res.json()["status"] in ["PRESENT", "LATE"]

    out_res = client.post("/attendance/check-out", json={
        "employee_id": unique_emp_id,
        "notes": "Leaving office"
    })
    assert out_res.status_code == 200
    assert out_res.json()["check_out"] is not None

