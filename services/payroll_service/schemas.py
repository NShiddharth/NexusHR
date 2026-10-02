from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime

class SalaryStructureBase(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    base_annual_salary: float
    monthly_base: Optional[float] = None
    housing_allowance: float = 500.0
    transport_allowance: float = 250.0
    medical_allowance: float = 200.0
    tax_percentage: float = 18.0
    pension_percentage: float = 5.0
    insurance_deduction: float = 150.0
    currency: str = "USD"

class SalaryStructureCreate(SalaryStructureBase):
    pass

class SalaryStructureResponse(SalaryStructureBase):
    id: str
    monthly_base: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PayslipGenerateRequest(BaseModel):
    employee_id: str
    employee_name: str
    department_id: Optional[str] = None
    pay_period: str # "2026-09"
    bonus: float = 0.0
    other_deductions: float = 0.0
    payment_method: str = "DIRECT_DEPOSIT"

class BatchPayrollRunRequest(BaseModel):
    pay_period: str
    bonus_percentage: float = 0.0

class PayslipResponse(BaseModel):
    id: str
    payslip_number: str
    employee_id: str
    employee_name: str
    department_id: Optional[str] = None
    pay_period: str
    payment_date: date
    basic_salary: float
    allowances: float
    bonus: float
    gross_salary: float
    tax_deduction: float
    pension_deduction: float
    insurance_deduction: float
    other_deductions: float
    total_deductions: float
    net_salary: float
    status: str
    payment_method: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PayrollMetrics(BaseModel):
    total_disbursed_period: str
    total_gross_disbursed: float
    total_net_disbursed: float
    total_tax_withheld: float
    total_payslips_issued: int
    avg_net_salary: float
