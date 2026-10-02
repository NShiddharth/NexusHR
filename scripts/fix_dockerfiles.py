from pathlib import Path

services = ['auth_service', 'department_service', 'employee_service', 'attendance_service', 'payroll_service', 'api_gateway']
ports = [8001, 8002, 8003, 8004, 8005, 8000]

for s, p in zip(services, ports):
    df_content = f"""FROM python:3.11-slim

WORKDIR /app

COPY services/shared /app/shared
COPY services/{s}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/{s} /app

EXPOSE {p}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{p}"]
"""
    (Path('services') / s / 'Dockerfile').write_text(df_content)

print("All Dockerfiles regenerated successfully.")
