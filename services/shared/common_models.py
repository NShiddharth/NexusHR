"""
Shared common models, security, and messaging utilities across microservices.
"""
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    HR_MANAGER = "HR_MANAGER"
    DEPT_MANAGER = "DEPT_MANAGER"
    DEPARTMENT_MANAGER = "DEPT_MANAGER" # Alias for backward compatibility
    EMPLOYEE = "EMPLOYEE"

class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    employee_id: Optional[str] = None
    exp: Optional[int] = None

class ApiResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EventMessage(BaseModel):
    event_id: str
    event_type: str
    source_service: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any]
