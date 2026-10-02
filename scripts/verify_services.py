"""
Automated verification script for testing all microservice health endpoints.
"""
import urllib.request
import json
import time

ENDPOINTS = [
    ("API Gateway", "http://127.0.0.1:8000/health"),
    ("Gateway Aggregated Status", "http://127.0.0.1:8000/api/gateway/services-status"),
    ("Auth Service", "http://127.0.0.1:8001/health"),
    ("Department Service", "http://127.0.0.1:8002/health"),
    ("Employee Service", "http://127.0.0.1:8003/health"),
    ("Attendance Service", "http://127.0.0.1:8004/health"),
    ("Payroll Service", "http://127.0.0.1:8005/health"),
]

import sys

def check_all():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("[*] Probing Microservices Health Status...")
    print("=" * 60)
    all_ok = True

    for name, url in ENDPOINTS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NexusHealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                status_code = resp.status
                data = json.loads(resp.read().decode('utf-8'))
                print(f"[OK] {name:28} [HTTP {status_code}] -> {data}")
        except Exception as e:
            print(f"[ERR] {name:28} [FAILED] -> {e}")
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("[SUCCESS] ALL MICROSERVICES ARE OPERATIONAL!")
    else:
        print("[WARNING] Some microservices were unreachable. Ensure they are running.")
    print("=" * 60)

if __name__ == "__main__":
    check_all()
