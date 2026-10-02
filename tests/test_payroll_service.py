import pytest
import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.payroll_service.main import app as payroll_app
from services.shared.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(payroll_app) as c:
        yield c

def get_admin_headers():
    token = create_access_token({"sub": "admin-1", "email": "admin@company.com", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_payroll_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "payroll-service"

def test_list_payslips(client):
    res = client.get("/payroll/payslips?pay_period=2026-09")
    assert res.status_code == 200
    slips = res.json()
    assert len(slips) >= 4
    for slip in slips:
        assert slip["gross_salary"] > slip["net_salary"]
        assert slip["tax_deduction"] > 0

def test_generate_single_payslip(client):
    headers = get_admin_headers()
    unique_suffix = str(uuid.uuid4())[:4]
    payload = {
        "employee_id": f"EMP-PAY-{unique_suffix}",
        "employee_name": "Test Pay User",
        "department_id": "ENG",
        "pay_period": f"2026-{unique_suffix}",
        "bonus": 1000.0,
        "other_deductions": 0.0
    }
    res = client.post("/payroll/generate", json=payload, headers=headers)
    assert res.status_code == 201
    slip = res.json()
    assert slip["employee_id"] == f"EMP-PAY-{unique_suffix}"
    assert slip["bonus"] == 1000.0
    assert slip["net_salary"] > 0

def test_batch_payroll_run(client):
    headers = get_admin_headers()
    unique_period = f"2027-{str(uuid.uuid4())[:4]}"
    payload = {
        "pay_period": unique_period,
        "bonus_percentage": 5.0
    }
    res = client.post("/payroll/batch-run", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["payslips_generated"] > 0

def test_payroll_metrics(client):
    res = client.get("/payroll/metrics?pay_period=2026-09")
    assert res.status_code == 200
    metrics = res.json()
    assert "total_gross_disbursed" in metrics
    assert "total_net_disbursed" in metrics
    assert metrics["total_payslips_issued"] >= 4

def test_payslip_not_found(client):
    res = client.get("/payroll/payslips/NON-EXISTENT-PAYSLIP-ID")
    assert res.status_code == 404

