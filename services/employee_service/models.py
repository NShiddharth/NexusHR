import uuid
import json
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, Text
try:
    from .database import Base
except (ImportError, ValueError):
    from database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    department_id = Column(String(50), nullable=False, index=True)
    department_name = Column(String(150), nullable=True)
    job_title = Column(String(150), nullable=False)
    role = Column(String(50), default="EMPLOYEE", nullable=False)
    hire_date = Column(Date, default=date.today)
    salary = Column(Float, default=75000.0)
    status = Column(String(50), default="ACTIVE")
    skills = Column(Text, default="[]")
    avatar_url = Column(String(500), nullable=True)
    manager_id = Column(String(50), nullable=True)
    performance_rating = Column(Float, default=4.5)
    location = Column(String(100), default="HQ")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def skills_list(self) -> list:
        try:
            return json.loads(self.skills) if self.skills else []
        except Exception:
            return []

    def set_skills(self, skills_list: list):
        self.skills = json.dumps(skills_list)
