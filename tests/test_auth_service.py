import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from services.auth_service.main import app as auth_app

@pytest.fixture(scope="module")
def client():
    with TestClient(auth_app) as c:
        yield c

def test_auth_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_success(client):
    response = client.post("/auth/login", json={
        "username_or_email": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"

def test_login_invalid_password(client):
    response = client.post("/auth/login", json={
        "username_or_email": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_user_me_endpoint(client):
    login_res = client.post("/auth/login", json={
        "username_or_email": "admin",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@company.com"

def test_unauthorized_missing_token(client):
    res = client.get("/auth/me")
    assert res.status_code == 401

def test_rbac_employee_forbidden_from_admin_users_list(client):
    # Log in as normal employee
    emp_res = client.post("/auth/login", json={
        "username_or_email": "employee",
        "password": "emp123"
    })
    emp_token = emp_res.json()["access_token"]

    # Attempting to access admin-only /auth/users should yield 403 Forbidden
    res = client.get("/auth/users", headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 403

def test_all_demo_accounts_authentication(client):
    accounts = [
        ("admin", "admin123", "ADMIN"),
        ("hrmanager", "hr123", "HR_MANAGER"),
        ("deptmanager", "manager123", "DEPT_MANAGER"),
        ("employee", "emp123", "EMPLOYEE"),
    ]
    for username, password, expected_role in accounts:
        res = client.post("/auth/login", json={"username_or_email": username, "password": password})
        assert res.status_code == 200, f"Demo account {username} failed to authenticate"
        data = res.json()
        assert data["user"]["role"] == expected_role
        assert "hashed_password" not in data["user"]

def test_legacy_sha256_hash_authentication_and_migration(client):
    import hashlib
    from services.auth_service.database import get_db
    from services.auth_service import models

    # Seed a test user with a raw legacy SHA-256 hash
    legacy_plain = "legacyPass123"
    legacy_sha = hashlib.sha256(legacy_plain.encode("utf-8")).hexdigest()
    
    db = next(get_db())
    try:
        # Delete if exists
        db.query(models.User).filter(models.User.username == "legacy_user").delete()
        db.commit()

        user = models.User(
            username="legacy_user",
            email="legacy@company.com",
            full_name="Legacy User",
            role="EMPLOYEE",
            hashed_password=legacy_sha,
            employee_id="EMP-LEGACY"
        )
        db.add(user)
        db.commit()

        # 1. Login with legacy hash
        res = client.post("/auth/login", json={"username_or_email": "legacy_user", "password": legacy_plain})
        assert res.status_code == 200
        assert "access_token" in res.json()

        # 2. Check that password was automatically upgraded to PBKDF2 in DB
        db.refresh(user)
        assert user.hashed_password.startswith("pbkdf2:sha256:600000$")

        # 3. Clean up
        db.delete(user)
        db.commit()
    finally:
        db.close()


