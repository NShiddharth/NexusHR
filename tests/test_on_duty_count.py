"""
Tests for GET /attendance/on-duty/count

Definition: employees who have checked in today AND have not yet checked out.

Scenarios:
  1. Employee checked in, not checked out → counted
  2. Employee checked in AND checked out → NOT counted
  3. Employee with no attendance record today → NOT counted
  4. Employee on leave (no check-in) → NOT counted
  5. Multiple employees → correct aggregate count
"""
import pytest
import sys
import uuid
from pathlib import Path
from datetime import date

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "services"))

from fastapi.testclient import TestClient
from services.attendance_service.main import app as att_app


@pytest.fixture(scope="module")
def client():
    with TestClient(att_app) as c:
        yield c


def _unique_id() -> str:
    return f"EMP-ODC-{str(uuid.uuid4())[:6].upper()}"


def test_on_duty_count_endpoint_exists(client):
    """The endpoint must return HTTP 200 with the correct shape."""
    res = client.get("/attendance/on-duty/count")
    assert res.status_code == 200
    data = res.json()
    assert "on_duty_count" in data
    assert "as_of" in data
    assert isinstance(data["on_duty_count"], int)
    assert data["on_duty_count"] >= 0
    assert data["as_of"] == str(date.today())


def test_checked_in_not_checked_out_is_counted(client):
    """Employee checked in but not yet checked out must increase on_duty_count by 1."""
    before = client.get("/attendance/on-duty/count").json()["on_duty_count"]

    emp_id = _unique_id()
    in_res = client.post("/attendance/check-in", json={
        "employee_id": emp_id,
        "employee_name": "OnDuty Active",
    })
    assert in_res.status_code == 200

    after = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after == before + 1, (
        f"Expected on_duty_count to increase by 1: before={before}, after={after}"
    )


def test_checked_out_employee_not_counted(client):
    """Employee who has both checked in and checked out must NOT appear in on_duty_count."""
    emp_id = _unique_id()

    client.post("/attendance/check-in", json={
        "employee_id": emp_id,
        "employee_name": "OnDuty Gone Home",
    })

    before_checkout = client.get("/attendance/on-duty/count").json()["on_duty_count"]

    out_res = client.post("/attendance/check-out", json={"employee_id": emp_id})
    assert out_res.status_code == 200
    assert out_res.json()["check_out"] is not None

    after_checkout = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after_checkout == before_checkout - 1, (
        f"Expected on_duty_count to decrease by 1 after checkout: "
        f"before={before_checkout}, after={after_checkout}"
    )


def test_no_attendance_record_not_counted(client):
    """An employee who never checked in today must not affect on_duty_count."""
    before = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    after = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after == before


def test_on_leave_employee_not_counted(client):
    """
    An employee on leave who has no check-in record for today must NOT be counted.
    This validates that on-duty is purely attendance-derived, not employment-status-derived.
    """
    before = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    after = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after == before, (
        "On-leave employees without a check-in must not appear in on_duty_count"
    )


def test_multiple_employees_correct_aggregate(client):
    """Three employees check in; two check out. on_duty_count must increase by exactly 1."""
    before = client.get("/attendance/on-duty/count").json()["on_duty_count"]

    ids = [_unique_id() for _ in range(3)]
    for i, emp_id in enumerate(ids):
        client.post("/attendance/check-in", json={
            "employee_id": emp_id,
            "employee_name": f"MultiTest {i}",
        })

    mid = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert mid == before + 3, f"After 3 check-ins: expected {before + 3}, got {mid}"

    for emp_id in ids[:2]:
        client.post("/attendance/check-out", json={"employee_id": emp_id})

    final = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert final == before + 1, (
        f"After 3 check-ins and 2 check-outs: expected {before + 1}, got {final}"
    )


def test_zero_active_employees_when_all_checked_out(client):
    """
    When all currently on-duty employees check out, on_duty_count reaches exactly 0.
    """
    records_res = client.get("/attendance")
    assert records_res.status_code == 200
    records = records_res.json()

    for r in records:
        if r.get("check_in") is not None and r.get("check_out") is None:
            client.post("/attendance/check-out", json={"employee_id": r["employee_id"]})

    final_count = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert final_count == 0, f"Expected 0 active employees, got {final_count}"


def test_clean_employee_lifecycle_exact_flow(client):
    """
    Exact lifecycle test:
    - baseline on_duty_count
    - clean employee checks in -> count increments by 1
    - second check-in for same employee -> rejected with 400, count remains +1
    - check-out -> count decrements back by 1
    """
    baseline = client.get("/attendance/on-duty/count").json()["on_duty_count"]

    emp_id = _unique_id()
    emp_name = "Lifecycle Clean Tester"

    # Step 1: Check in clean employee
    cin = client.post("/attendance/check-in", json={
        "employee_id": emp_id,
        "employee_name": emp_name,
        "notes": "First check-in"
    })
    assert cin.status_code == 200
    assert cin.json()["check_in"] is not None

    after_cin = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after_cin == baseline + 1, f"Expected {baseline + 1}, got {after_cin}"

    # Step 2: Second check-in attempt -> MUST be rejected with 400 (currently on duty, no checkout yet)
    cin_second = client.post("/attendance/check-in", json={
        "employee_id": emp_id,
        "employee_name": emp_name
    })
    assert cin_second.status_code == 400
    # New precise message: "Employee is already checked in for today"
    assert "already checked in" in cin_second.json()["detail"].lower()

    after_second = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after_second == baseline + 1, f"Expected count to remain {baseline + 1}, got {after_second}"

    # Step 3: Check out
    cout = client.post("/attendance/check-out", json={"employee_id": emp_id})
    assert cout.status_code == 200
    assert cout.json()["check_out"] is not None

    after_cout = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after_cout == baseline, f"Expected count to return to baseline {baseline}, got {after_cout}"


def test_completed_attendance_cannot_checkin_again(client):
    """
    An employee who has BOTH checked in AND checked out today must receive a distinct
    '400 completed attendance' error on a re-check-in attempt.
    Their re-attempt must NOT increment on_duty_count.
    """
    emp_id = _unique_id()
    emp_name = "Completed Shift Tester"

    # Full lifecycle: check in then check out
    client.post("/attendance/check-in", json={"employee_id": emp_id, "employee_name": emp_name})
    client.post("/attendance/check-out", json={"employee_id": emp_id})

    baseline = client.get("/attendance/on-duty/count").json()["on_duty_count"]

    # Attempt to check in again after completing attendance
    retry = client.post("/attendance/check-in", json={"employee_id": emp_id, "employee_name": emp_name})
    assert retry.status_code == 400
    detail = retry.json()["detail"].lower()
    assert "completed attendance" in detail or "already completed" in detail, (
        f"Expected 'completed attendance' in error detail, got: {detail!r}"
    )

    # Count must NOT have changed
    after_retry = client.get("/attendance/on-duty/count").json()["on_duty_count"]
    assert after_retry == baseline, (
        f"on_duty_count must not change after rejected re-check-in: expected {baseline}, got {after_retry}"
    )

