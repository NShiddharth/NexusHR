FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY services/shared /app/services/shared
COPY services/__init__.py /app/services/__init__.py
COPY services/shared /app/shared
COPY services/api_gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api_gateway /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
