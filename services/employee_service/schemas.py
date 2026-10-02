from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class EmployeeBase(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    department_id: str
    department_name: Optional[str] = None
    job_title: str
    role: str = "EMPLOYEE"
    hire_date: date = date.today()
    salary: float = 75000.0
    status: str = "ACTIVE" # ACTIVE, ON_LEAVE, TERMINATED
    skills: List[str] = []
    avatar_url: Optional[str] = None
    manager_id: Optional[str] = None
    performance_rating: float = 4.5
    location: str = "HQ"

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    role: Optional[str] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None
    status: Optional[str] = None
    skills: Optional[List[str]] = None
    avatar_url: Optional[str] = None
    manager_id: Optional[str] = None
    performance_rating: Optional[float] = None
    location: Optional[str] = None

class EmployeeResponse(BaseModel):
    id: str
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    department_id: str
    department_name: Optional[str] = None
    job_title: str
    role: str
    hire_date: date
    salary: float
    status: str
    skills: List[str]
    avatar_url: Optional[str] = None
    manager_id: Optional[str] = None
    performance_rating: float
    location: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmployeeStats(BaseModel):
    total_employees: int
    active_employees: int
    on_leave_employees: int
    terminated_employees: int
    avg_salary: float
    total_payroll_budget: float
    department_headcounts: Dict[str, int]
