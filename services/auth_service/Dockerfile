FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY services/shared /app/services/shared
COPY services/__init__.py /app/services/__init__.py
COPY services/shared /app/shared
COPY services/auth_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/auth_service /app

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
