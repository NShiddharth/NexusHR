import os
import sys
import time
import httpx
from pathlib import Path
from typing import Optional
import redis

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.shared.common_models import ApiResponse
from services.shared.security import decode_access_token

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
DEPARTMENT_SERVICE_URL = os.getenv("DEPARTMENT_SERVICE_URL", "http://localhost:8002")
EMPLOYEE_SERVICE_URL = os.getenv("EMPLOYEE_SERVICE_URL", "http://localhost:8003")
ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://localhost:8004")
PAYROLL_SERVICE_URL = os.getenv("PAYROLL_SERVICE_URL", "http://localhost:8005")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

SERVICES_MAP = {
    "auth-service": {"url": AUTH_SERVICE_URL, "port": 8001, "desc": "Authentication & Identity"},
    "department-service": {"url": DEPARTMENT_SERVICE_URL, "port": 8002, "desc": "Department & Hierarchy"},
    "employee-service": {"url": EMPLOYEE_SERVICE_URL, "port": 8003, "desc": "Employee Profiles & Directory"},
    "attendance-service": {"url": ATTENDANCE_SERVICE_URL, "port": 8004, "desc": "Time Tracking & Leave Approvals"},
    "payroll-service": {"url": PAYROLL_SERVICE_URL, "port": 8005, "desc": "Compensation & Payslip Engine"},
}

# Redis Client for distributed rate limiting & caching
redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.0)
    redis_client.ping()
    print("Redis client connected successfully for API Gateway rate-limiting.")
except Exception as e:
    redis_client = None
    print(f"Redis not available locally ({e}), falling back to in-memory rate limiter.")

app = FastAPI(
    title="Employee Management Microservices API Gateway",
    description="Unified API Gateway with Intelligent Reverse Routing, Health Aggregation, Redis Caching & Rate Limiting",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory rate limiting fallback
RATE_LIMIT_STORE = {}
RATE_LIMIT_WINDOW = 60 # seconds
RATE_LIMIT_MAX_REQUESTS = 300

@app.middleware("http")
async def rate_limiting_and_timing_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Distributed Redis Rate Limiting
    is_limited = False
    if redis_client:
        try:
            key = f"rate_limit:{client_ip}"
            current_count = redis_client.incr(key)
            if current_count == 1:
                redis_client.expire(key, RATE_LIMIT_WINDOW)
            if current_count > RATE_LIMIT_MAX_REQUESTS:
                is_limited = True
        except Exception:
            # Fallback to local memory if redis has intermittent issue
            pass

    if not is_limited:
        req_history = RATE_LIMIT_STORE.get(client_ip, [])
        req_history = [t for t in req_history if current_time - t < RATE_LIMIT_WINDOW]
        if len(req_history) >= RATE_LIMIT_MAX_REQUESTS:
            is_limited = True
        else:
            req_history.append(current_time)
            RATE_LIMIT_STORE[client_ip] = req_history

    if is_limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Maximum 300 requests/min. Try again in 60 seconds."}
        )

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Gateway"] = "FastAPI-Microservices-Gateway-v1"
    return response

# Forwarding helper
async def forward_request(target_url: str, request: Request) -> Response:
    client = httpx.AsyncClient(timeout=15.0)
    try:
        headers = dict(request.headers)
        headers.pop("host", None)
        
        body = await request.body()
        
        res = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        response_headers = {
            k: v for k, v in res.headers.items() 
            if k.lower() not in ["content-length", "transfer-encoding", "content-encoding"]
        }
        
        return Response(
            content=res.content,
            status_code=res.status_code,
            headers=response_headers,
            media_type=res.headers.get("content-type")
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Downstream service unavailable at {target_url}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gateway forwarding error: {str(e)}"
        )
    finally:
        await client.aclose()

@app.get("/health")
def gateway_health():
    return {"status": "healthy", "service": "api-gateway", "version": "1.0.0"}

@app.get("/api/gateway/services-status")
async def get_all_services_status():
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, meta in SERVICES_MAP.items():
            start = time.time()
            try:
                res = await client.get(f"{meta['url']}/health")
                latency_ms = round((time.time() - start) * 1000, 2)
                if res.status_code == 200:
                    results[name] = {
                        "status": "UP",
                        "latency_ms": latency_ms,
                        "url": meta["url"],
                        "description": meta["desc"]
                    }
                else:
                    results[name] = {
                        "status": "DEGRADED",
                        "code": res.status_code,
                        "url": meta["url"],
                        "description": meta["desc"]
                    }
            except Exception as e:
                results[name] = {
                    "status": "DOWN",
                    "error": str(e),
                    "url": meta["url"],
                    "description": meta["desc"]
                }
    return results

# Auth Service Routes
@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_auth(path: str, request: Request):
    target = f"{AUTH_SERVICE_URL}/auth/{path}"
    return await forward_request(target, request)

# Department Service Routes
@app.api_route("/api/departments", methods=["GET", "POST"])
@app.api_route("/api/departments/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_departments(request: Request, path: str = ""):
    target = f"{DEPARTMENT_SERVICE_URL}/departments" if not path else f"{DEPARTMENT_SERVICE_URL}/departments/{path}"
    return await forward_request(target, request)

# Employee Service Routes
@app.api_route("/api/employees", methods=["GET", "POST"])
@app.api_route("/api/employees/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_employees(request: Request, path: str = ""):
    target = f"{EMPLOYEE_SERVICE_URL}/employees" if not path else f"{EMPLOYEE_SERVICE_URL}/employees/{path}"
    return await forward_request(target, request)

# Attendance & Review Routes
@app.api_route("/api/attendance", methods=["GET"])
@app.api_route("/api/attendance/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_attendance(request: Request, path: str = ""):
    target = f"{ATTENDANCE_SERVICE_URL}/attendance" if not path else f"{ATTENDANCE_SERVICE_URL}/attendance/{path}"
    return await forward_request(target, request)

@app.api_route("/api/leaves", methods=["GET", "POST"])
@app.api_route("/api/leaves/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_leaves(request: Request, path: str = ""):
    target = f"{ATTENDANCE_SERVICE_URL}/leaves" if not path else f"{ATTENDANCE_SERVICE_URL}/leaves/{path}"
    return await forward_request(target, request)

@app.api_route("/api/reviews", methods=["GET", "POST"])
@app.api_route("/api/reviews/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_reviews(request: Request, path: str = ""):
    target = f"{ATTENDANCE_SERVICE_URL}/reviews" if not path else f"{ATTENDANCE_SERVICE_URL}/reviews/{path}"
    return await forward_request(target, request)

# Payroll Routes
@app.api_route("/api/payroll/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_payroll(path: str, request: Request):
    target = f"{PAYROLL_SERVICE_URL}/payroll/{path}"
    return await forward_request(target, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
