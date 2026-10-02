"""
Live API Gateway verification script.
"""
import sys
import urllib.request
import json
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000/api"

def main():
    print("=" * 60)
    print("Testing Live API Gateway & Downstream Services Integration")
    print("=" * 60)

    # 1. Login via Gateway
    login_req = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=json.dumps({"username_or_email": "admin", "password": "admin123"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as res:
        login_data = json.loads(res.read().decode("utf-8"))
        token = login_data["access_token"]
        role = login_data["user"]["role"]
        print(f"[1/7] Live Gateway Login: OK (Role: {role})")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Get User Profile via Gateway
    me_req = urllib.request.Request(f"{BASE_URL}/auth/me", headers=headers)
    with urllib.request.urlopen(me_req) as res:
        me_data = json.loads(res.read().decode("utf-8"))
        print(f"[2/7] Live Gateway Auth Profile (/auth/me): OK (Email: {me_data['email']})")

    # 3. List Departments via Gateway
    dept_req = urllib.request.Request(f"{BASE_URL}/departments", headers=headers)
    with urllib.request.urlopen(dept_req) as res:
        dept_data = json.loads(res.read().decode("utf-8"))
        print(f"[3/7] Live Gateway Departments (/departments): OK (Count: {len(dept_data)})")

    # 4. List Employees via Gateway
    emp_req = urllib.request.Request(f"{BASE_URL}/employees", headers=headers)
    with urllib.request.urlopen(emp_req) as res:
        emp_data = json.loads(res.read().decode("utf-8"))
        print(f"[4/7] Live Gateway Employees (/employees): OK (Count: {len(emp_data)})")

    # 5. Attendance Overview via Gateway
    att_req = urllib.request.Request(f"{BASE_URL}/attendance/overview", headers=headers)
    with urllib.request.urlopen(att_req) as res:
        att_data = json.loads(res.read().decode("utf-8"))
        print(f"[5/7] Live Gateway Attendance (/attendance/overview): OK (Present: {att_data['today_present']})")

    # 6. Apply Leave via Gateway
    leave_payload = {
        "employee_id": f"EMP-LIVE-{str(uuid.uuid4())[:4]}",
        "employee_name": "Live Tester",
        "leave_type": "CASUAL",
        "start_date": "2026-10-15",
        "end_date": "2026-10-16",
        "reason": "Live gateway automated verification"
    }
    leave_req = urllib.request.Request(
        f"{BASE_URL}/leaves",
        data=json.dumps(leave_payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(leave_req) as res:
        leave_data = json.loads(res.read().decode("utf-8"))
        print(f"[6/7] Live Gateway Leave Application (/leaves): OK (Status: {leave_data['status']})")

    # 7. Payroll Metrics via Gateway
    pay_req = urllib.request.Request(f"{BASE_URL}/payroll/metrics", headers=headers)
    with urllib.request.urlopen(pay_req) as res:
        pay_data = json.loads(res.read().decode("utf-8"))
        print(f"[7/7] Live Gateway Payroll Metrics (/payroll/metrics): OK (Gross: ${pay_data['total_gross_disbursed']})")

    print("=" * 60)
    print("ALL 7 LIVE GATEWAY & DOWNSTREAM WORKFLOWS SUCCEEDED!")
    print("=" * 60)

if __name__ == "__main__":
    main()
