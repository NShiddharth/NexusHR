"""
Local multi-service launcher for running all microservices concurrently without Docker.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

SERVICES = [
    ("Auth Service", "services/auth_service", "main:app", 8001),
    ("Department Service", "services/department_service", "main:app", 8002),
    ("Employee Service", "services/employee_service", "main:app", 8003),
    ("Attendance Service", "services/attendance_service", "main:app", 8004),
    ("Payroll Service", "services/payroll_service", "main:app", 8005),
    ("API Gateway", "services/api_gateway", "main:app", 8000),
]

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root_dir = Path(__file__).resolve().parent.parent
    processes = []

    print("=" * 60)
    print("[+] Launching NexusHR Microservices Cluster Locally...")
    print("=" * 60)

    try:
        for name, folder, app, port in SERVICES:
            cwd = root_dir / folder
            cmd = [sys.executable, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)]
            print(f"[*] Starting {name} on http://127.0.0.1:{port}...")
            p = subprocess.Popen(cmd, cwd=str(cwd), env={**os.environ, "PYTHONPATH": str(root_dir)})
            processes.append((name, p))
            time.sleep(0.8)

        print("\n" + "=" * 60)
        print("[SUCCESS] All Microservices are active!")
        print(" -> API Gateway: http://127.0.0.1:8000")
        print(" -> Frontend Dashboard: open frontend/index.html in browser")
        print("=" * 60)
        print("Press Ctrl+C to stop all services.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping all microservices...")
        for name, p in processes:
            p.terminate()
            p.wait()
        print("All services stopped.")

if __name__ == "__main__":
    main()
