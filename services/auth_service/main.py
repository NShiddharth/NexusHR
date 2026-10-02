import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

try:
    from . import models, schemas
    from .database import engine, Base, get_db
except (ImportError, ValueError):
    import models
    import schemas
    from database import engine, Base, get_db

from services.shared.common_models import UserRole, TokenPayload
from services.shared.security import create_access_token, decode_access_token, get_current_user, require_roles

import hmac
import secrets

# Create database tables
Base.metadata.create_all(bind=engine)

# OWASP Password Storage Cheat Sheet: PBKDF2-HMAC-SHA256 minimum work factor is 600,000 iterations.
# Source: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
PBKDF2_ITERATIONS = 600_000

def get_password_hash(password: str) -> str:
    """Generate cryptographically secure salted PBKDF2-HMAC-SHA256 hash.
    Work factor: 600,000 iterations (OWASP minimum as of 2024-2026).
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${key}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using constant-time comparison against PBKDF2 or legacy hash."""
    if hashed_password.startswith("pbkdf2:sha256:"):
        try:
            parts = hashed_password.split("$")
            if len(parts) == 3:
                header, salt, key = parts
                _, _, iterations = header.split(":")
                computed_key = hashlib.pbkdf2_hmac(
                    'sha256',
                    plain_password.encode('utf-8'),
                    salt.encode('utf-8'),
                    int(iterations)
                ).hex()
                return hmac.compare_digest(computed_key, key)
        except Exception:
            return False
    # Backward compatibility with legacy SHA-256
    legacy_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, hashed_password)

def seed_default_users(db: Session):
    admin_exists = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_exists:
        users = [
            models.User(
                username="admin",
                email="admin@company.com",
                full_name="System Administrator",
                role="ADMIN",
                hashed_password=get_password_hash("admin123"),
                employee_id="EMP-001"
            ),
            models.User(
                username="hrmanager",
                email="hr@company.com",
                full_name="Sarah Jenkins",
                role="HR_MANAGER",
                hashed_password=get_password_hash("hr123"),
                employee_id="EMP-002"
            ),
            models.User(
                username="deptmanager",
                email="manager@company.com",
                full_name="David Chen",
                role="DEPT_MANAGER",
                hashed_password=get_password_hash("manager123"),
                employee_id="EMP-003"
            ),
            models.User(
                username="employee",
                email="alex@company.com",
                full_name="Alex Rivera",
                role="EMPLOYEE",
                hashed_password=get_password_hash("emp123"),
                employee_id="EMP-004"
            ),
        ]
        db.add_all(users)
        db.commit()
        print("Default users seeded successfully into Auth DB.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(get_db())
    try:
        seed_default_users(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Auth Microservice",
    description="Authentication, User Identity & RBAC Token Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service", "version": "1.0.0"}

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    new_user = models.User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        role=user_in.role.upper(),
        employee_id=user_in.employee_id,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=schemas.Token)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # If DB is empty for test cases, seed on-demand
    if db.query(models.User).count() == 0:
        seed_default_users(db)

    user = db.query(models.User).filter(
        (models.User.username == login_data.username_or_email) | 
        (models.User.email == login_data.username_or_email)
    ).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    # Auto-upgrade legacy SHA-256 hash to salted PBKDF2 on successful login
    if not user.hashed_password.startswith("pbkdf2:sha256:"):
        user.hashed_password = get_password_hash(login_data.password)
        db.commit()

    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "employee_id": user.employee_id,
        "username": user.username,
        "full_name": user.full_name
    }
    access_token = create_access_token(data=token_data)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: TokenPayload = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == current_user.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/auth/users", response_model=list[schemas.UserResponse])
def get_all_users(
    skip: int = 0, 
    limit: int = 100, 
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])), 
    db: Session = Depends(get_db)
):
    return db.query(models.User).offset(skip).limit(limit).all()

@app.put("/auth/change-password")
def change_password(
    pwd_data: schemas.PasswordChange,
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == current_user.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(pwd_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
