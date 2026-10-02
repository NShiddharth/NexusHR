import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, Text
try:
    from .database import Base
except (ImportError, ValueError):
    from database import Base

class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    employee_name = Column(String(150), nullable=True)
    base_annual_salary = Column(Float, default=75000.0, nullable=False)
    monthly_base = Column(Float, default=6250.0, nullable=False)
    housing_allowance = Column(Float, default=500.0)
    transport_allowance = Column(Float, default=250.0)
    medical_allowance = Column(Float, default=200.0)
    tax_percentage = Column(Float, default=18.0)
    pension_percentage = Column(Float, default=5.0)
    insurance_deduction = Column(Float, default=150.0)
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Payslip(Base):
    __tablename__ = "payslips"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payslip_number = Column(String(50), unique=True, index=True, nullable=False)
    employee_id = Column(String(50), index=True, nullable=False)
    employee_name = Column(String(150), nullable=False)
    department_id = Column(String(50), nullable=True)
    pay_period = Column(String(20), index=True, nullable=False)
    payment_date = Column(Date, default=date.today)
    
    basic_salary = Column(Float, nullable=False)
    allowances = Column(Float, default=0.0)
    bonus = Column(Float, default=0.0)
    gross_salary = Column(Float, nullable=False)
    
    tax_deduction = Column(Float, default=0.0)
    pension_deduction = Column(Float, default=0.0)
    insurance_deduction = Column(Float, default=0.0)
    other_deductions = Column(Float, default=0.0)
    total_deductions = Column(Float, nullable=False)
    
    net_salary = Column(Float, nullable=False)
    status = Column(String(30), default="PAID")
    payment_method = Column(String(50), default="DIRECT_DEPOSIT")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
