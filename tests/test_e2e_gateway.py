import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.api_gateway.main import app as gateway_app

@pytest.fixture(scope="module")
def client():
    with TestClient(gateway_app) as c:
        yield c

def test_gateway_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "api-gateway"

def test_gateway_services_status_endpoint(client):
    res = client.get("/api/gateway/services-status")
    assert res.status_code == 200
    status_map = res.json()
    assert "auth-service" in status_map
    assert "department-service" in status_map
    assert "employee-service" in status_map
    assert "attendance-service" in status_map
    assert "payroll-service" in status_map
