import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, date, timezone
from contextlib import asynccontextmanager

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from . import models, schemas
    from .database import engine, Base, get_db
except (ImportError, ValueError):
    import models
    import schemas
    from database import engine, Base, get_db

from services.shared.common_models import UserRole, TokenPayload
from services.shared.security import get_current_user, require_roles
from services.shared.event_bus import event_bus

Base.metadata.create_all(bind=engine)

def calculate_payslip_breakdown(
    salary_struct: models.SalaryStructure,
    bonus: float = 0.0,
    other_deductions: float = 0.0
) -> dict:
    basic = round(salary_struct.monthly_base, 2)
    total_allowances = round(
        salary_struct.housing_allowance + 
        salary_struct.transport_allowance + 
        salary_struct.medical_allowance, 2
    )
    gross = round(basic + total_allowances + bonus, 2)
    
    # Calculate taxes and deductions
    tax = round(gross * (salary_struct.tax_percentage / 100.0), 2)
    pension = round(basic * (salary_struct.pension_percentage / 100.0), 2)
    insurance = round(salary_struct.insurance_deduction, 2)
    
    total_deductions = round(tax + pension + insurance + other_deductions, 2)
    net = round(gross - total_deductions, 2)
    
    return {
        "basic_salary": basic,
        "allowances": total_allowances,
        "bonus": bonus,
        "gross_salary": gross,
        "tax_deduction": tax,
        "pension_deduction": pension,
        "insurance_deduction": insurance,
        "other_deductions": other_deductions,
        "total_deductions": total_deductions,
        "net_salary": net
    }

def seed_default_payroll(db: Session):
    if db.query(models.SalaryStructure).count() == 0:
        seed_salaries = [
            models.SalaryStructure(
                employee_id="EMP-001",
                employee_name="Alexander Vance",
                base_annual_salary=185000.0,
                monthly_base=round(185000.0 / 12, 2),
                housing_allowance=1200.0,
                transport_allowance=400.0,
                medical_allowance=350.0,
                tax_percentage=24.0,
                pension_percentage=6.0,
                insurance_deduction=250.0
            ),
            models.SalaryStructure(
                employee_id="EMP-002",
                employee_name="Sarah Jenkins",
                base_annual_salary=140000.0,
                monthly_base=round(140000.0 / 12, 2),
                housing_allowance=900.0,
                transport_allowance=300.0,
                medical_allowance=250.0,
                tax_percentage=20.0,
                pension_percentage=5.0,
                insurance_deduction=200.0
            ),
            models.SalaryStructure(
                employee_id="EMP-003",
                employee_name="David Chen",
                base_annual_salary=165000.0,
                monthly_base=round(165000.0 / 12, 2),
                housing_allowance=1000.0,
                transport_allowance=350.0,
                medical_allowance=300.0,
                tax_percentage=22.0,
                pension_percentage=5.5,
                insurance_deduction=220.0
            ),
            models.SalaryStructure(
                employee_id="EMP-004",
                employee_name="Alex Rivera",
                base_annual_salary=125000.0,
                monthly_base=round(125000.0 / 12, 2),
                housing_allowance=800.0,
                transport_allowance=250.0,
                medical_allowance=200.0,
                tax_percentage=18.0,
                pension_percentage=5.0,
                insurance_deduction=180.0
            ),
        ]
        db.add_all(seed_salaries)
        db.commit()

    if db.query(models.Payslip).count() == 0:
        structures = db.query(models.SalaryStructure).all()
        for struct in structures:
            breakdown = calculate_payslip_breakdown(struct, bonus=500.0)
            slip = models.Payslip(
                payslip_number=f"PAY-202609-{struct.employee_id}",
                employee_id=struct.employee_id,
                employee_name=struct.employee_name,
                pay_period="2026-09",
                payment_date=date(2026, 9, 30),
                status="PAID",
                payment_method="DIRECT_DEPOSIT",
                **breakdown
            )
            db.add(slip)
        db.commit()
        print("Default payroll structures and payslips seeded successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(get_db())
    try:
        seed_default_payroll(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Payroll Microservice",
    description="Compensation Structures, Tax Deductions, Payslip Generation & Disbursement Analytics",
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
    return {"status": "healthy", "service": "payroll-service", "version": "1.0.0"}

@app.get("/payroll/structures", response_model=list[schemas.SalaryStructureResponse])
def list_salary_structures(db: Session = Depends(get_db)):
    if db.query(models.SalaryStructure).count() == 0:
        seed_default_payroll(db)
    return db.query(models.SalaryStructure).all()

@app.get("/payroll/structures/{employee_id}", response_model=schemas.SalaryStructureResponse)
def get_salary_structure(employee_id: str, db: Session = Depends(get_db)):
    if db.query(models.SalaryStructure).count() == 0:
        seed_default_payroll(db)

    struct = db.query(models.SalaryStructure).filter(models.SalaryStructure.employee_id == employee_id).first()
    if not struct:
        raise HTTPException(status_code=404, detail="Salary structure not found for this employee")
    return struct

@app.post("/payroll/structures", response_model=schemas.SalaryStructureResponse, status_code=status.HTTP_201_CREATED)
def create_salary_structure(
    struct_in: schemas.SalaryStructureCreate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    existing = db.query(models.SalaryStructure).filter(models.SalaryStructure.employee_id == struct_in.employee_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Salary structure already configured for this employee")

    data = struct_in.model_dump()
    if not data.get("monthly_base"):
        data["monthly_base"] = round(data["base_annual_salary"] / 12, 2)

    new_struct = models.SalaryStructure(**data)
    db.add(new_struct)
    db.commit()
    db.refresh(new_struct)
    return new_struct

@app.get("/payroll/payslips", response_model=list[schemas.PayslipResponse])
def list_payslips(
    employee_id: str = Query(None),
    pay_period: str = Query(None),
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if db.query(models.Payslip).count() == 0:
        seed_default_payroll(db)

    query = db.query(models.Payslip)
    if employee_id:
        query = query.filter(models.Payslip.employee_id == employee_id)
    if pay_period:
        query = query.filter(models.Payslip.pay_period == pay_period)
    return query.order_by(models.Payslip.created_at.desc()).limit(limit).all()

@app.get("/payroll/payslips/{payslip_id}", response_model=schemas.PayslipResponse)
def get_payslip(payslip_id: str, db: Session = Depends(get_db)):
    slip = db.query(models.Payslip).filter(
        (models.Payslip.id == payslip_id) | (models.Payslip.payslip_number == payslip_id)
    ).first()
    if not slip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return slip

@app.post("/payroll/generate", response_model=schemas.PayslipResponse, status_code=status.HTTP_201_CREATED)
async def generate_payslip(
    req: schemas.PayslipGenerateRequest,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    if db.query(models.SalaryStructure).count() == 0:
        seed_default_payroll(db)

    struct = db.query(models.SalaryStructure).filter(models.SalaryStructure.employee_id == req.employee_id).first()
    if not struct:
        # Create default structure if not present
        struct = models.SalaryStructure(
            employee_id=req.employee_id,
            employee_name=req.employee_name,
            base_annual_salary=80000.0,
            monthly_base=round(80000.0 / 12, 2)
        )
        db.add(struct)
        db.commit()
        db.refresh(struct)

    breakdown = calculate_payslip_breakdown(struct, bonus=req.bonus, other_deductions=req.other_deductions)
    payslip_num = f"PAY-{req.pay_period.replace('-', '')}-{req.employee_id}-{str(uuid.uuid4())[:4].upper()}"

    slip = models.Payslip(
        payslip_number=payslip_num,
        employee_id=req.employee_id,
        employee_name=req.employee_name,
        department_id=req.department_id,
        pay_period=req.pay_period,
        payment_date=date.today(),
        status="PAID",
        payment_method=req.payment_method,
        **breakdown
    )
    db.add(slip)
    db.commit()
    db.refresh(slip)

    await event_bus.publish(
        event_type="payroll.disbursed",
        payload={
            "payslip_number": slip.payslip_number,
            "employee_id": slip.employee_id,
            "net_salary": slip.net_salary,
            "pay_period": slip.pay_period
        },
        source_service="payroll-service"
    )

    return slip

@app.post("/payroll/batch-run")
async def batch_payroll_run(
    req: schemas.BatchPayrollRunRequest,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    if db.query(models.SalaryStructure).count() == 0:
        seed_default_payroll(db)

    structures = db.query(models.SalaryStructure).all()
    created_count = 0
    total_net = 0.0

    for struct in structures:
        # Check if already generated for this period
        existing = db.query(models.Payslip).filter(
            models.Payslip.employee_id == struct.employee_id,
            models.Payslip.pay_period == req.pay_period
        ).first()

        if not existing:
            bonus = (struct.monthly_base * (req.bonus_percentage / 100.0)) if req.bonus_percentage > 0 else 0.0
            breakdown = calculate_payslip_breakdown(struct, bonus=round(bonus, 2))
            payslip_num = f"PAY-{req.pay_period.replace('-', '')}-{struct.employee_id}-{str(uuid.uuid4())[:4].upper()}"

            slip = models.Payslip(
                payslip_number=payslip_num,
                employee_id=struct.employee_id,
                employee_name=struct.employee_name or "Employee",
                pay_period=req.pay_period,
                payment_date=date.today(),
                status="PAID",
                payment_method="DIRECT_DEPOSIT",
                **breakdown
            )
            db.add(slip)
            created_count += 1
            total_net += breakdown["net_salary"]

    db.commit()

    await event_bus.publish(
        event_type="payroll.batch_completed",
        payload={"pay_period": req.pay_period, "payslips_generated": created_count, "total_net": total_net},
        source_service="payroll-service"
    )

    return {
        "success": True,
        "pay_period": req.pay_period,
        "payslips_generated": created_count,
        "total_net_disbursed": round(total_net, 2)
    }

@app.get("/payroll/metrics", response_model=schemas.PayrollMetrics)
def get_payroll_metrics(
    pay_period: str = Query(default="2026-09"),
    db: Session = Depends(get_db)
):
    if db.query(models.Payslip).count() == 0:
        seed_default_payroll(db)

    slips = db.query(models.Payslip).filter(models.Payslip.pay_period == pay_period).all()
    
    total_gross = sum(s.gross_salary for s in slips)
    total_net = sum(s.net_salary for s in slips)
    total_tax = sum(s.tax_deduction for s in slips)
    count = len(slips)
    avg_net = (total_net / count) if count > 0 else 0.0

    return {
        "total_disbursed_period": pay_period,
        "total_gross_disbursed": round(total_gross, 2),
        "total_net_disbursed": round(total_net, 2),
        "total_tax_withheld": round(total_tax, 2),
        "total_payslips_issued": count,
        "avg_net_salary": round(avg_net, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
