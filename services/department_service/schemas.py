from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    budget: float = 0.0
    location: str = "Headquarters"
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    budget: Optional[float] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentResponse(DepartmentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DepartmentStats(BaseModel):
    total_departments: int
    active_departments: int
    total_budget: float
    avg_budget_per_dept: float
