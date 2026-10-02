import os
import sys
import json
from pathlib import Path
from datetime import date
from contextlib import asynccontextmanager

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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

def format_employee_response(emp: models.Employee) -> dict:
    return {
        "id": emp.id,
        "employee_id": emp.employee_id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "full_name": emp.full_name,
        "email": emp.email,
        "phone": emp.phone,
        "department_id": emp.department_id,
        "department_name": emp.department_name,
        "job_title": emp.job_title,
        "role": emp.role,
        "hire_date": emp.hire_date,
        "salary": emp.salary,
        "status": emp.status,
        "skills": emp.skills_list,
        "avatar_url": emp.avatar_url,
        "manager_id": emp.manager_id,
        "performance_rating": emp.performance_rating,
        "location": emp.location,
        "created_at": emp.created_at,
        "updated_at": emp.updated_at
    }

def seed_default_employees(db: Session):
    if db.query(models.Employee).count() == 0:
        seed_data = [
            models.Employee(
                employee_id="EMP-001",
                first_name="Alexander",
                last_name="Vance",
                email="admin@company.com",
                phone="+1 (555) 019-2831",
                department_id="ENG",
                department_name="Engineering & Technology",
                job_title="Chief Technology Officer",
                role="ADMIN",
                hire_date=date(2021, 1, 15),
                salary=185000.0,
                status="ACTIVE",
                skills=json.dumps(["Architecture", "Kubernetes", "Cloud Governance", "Python", "Go"]),
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                performance_rating=4.9,
                location="San Francisco HQ"
            ),
            models.Employee(
                employee_id="EMP-002",
                first_name="Sarah",
                last_name="Jenkins",
                email="hr@company.com",
                phone="+1 (555) 019-3342",
                department_id="HR",
                department_name="Human Resources & People Ops",
                job_title="VP of People Operations",
                role="HR_MANAGER",
                hire_date=date(2021, 3, 1),
                salary=140000.0,
                status="ACTIVE",
                skills=json.dumps(["Talent Strategy", "Compensation & Benefits", "Leadership Coaching", "HRIS"]),
                avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
                performance_rating=4.8,
                location="Austin HQ"
            ),
            models.Employee(
                employee_id="EMP-003",
                first_name="David",
                last_name="Chen",
                email="manager@company.com",
                phone="+1 (555) 019-8871",
                department_id="ENG",
                department_name="Engineering & Technology",
                job_title="Engineering Director",
                role="DEPT_MANAGER",
                hire_date=date(2021, 6, 10),
                salary=165000.0,
                status="ACTIVE",
                skills=json.dumps(["Distributed Systems", "FastAPI", "PostgreSQL", "Team Mentorship"]),
                avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
                manager_id="EMP-001",
                performance_rating=4.7,
                location="San Francisco HQ"
            ),
            models.Employee(
                employee_id="EMP-004",
                first_name="Alex",
                last_name="Rivera",
                email="alex@company.com",
                phone="+1 (555) 019-5512",
                department_id="ENG",
                department_name="Engineering & Technology",
                job_title="Senior Full-Stack Engineer",
                role="EMPLOYEE",
                hire_date=date(2022, 2, 20),
                salary=125000.0,
                status="ACTIVE",
                skills=json.dumps(["React", "FastAPI", "TypeScript", "Docker", "TailwindCSS"]),
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
                manager_id="EMP-003",
                performance_rating=4.6,
                location="Remote / Denver"
            ),
            models.Employee(
                employee_id="EMP-005",
                first_name="Elena",
                last_name="Rostova",
                email="elena@company.com",
                phone="+1 (555) 019-6633",
                department_id="FIN",
                department_name="Finance, Accounting & Payroll",
                job_title="Head of Financial Planning & Analysis",
                role="DEPT_MANAGER",
                hire_date=date(2021, 9, 15),
                salary=145000.0,
                status="ACTIVE",
                skills=json.dumps(["Financial Modeling", "Payroll Audit", "Forecasting", "Risk Management"]),
                avatar_url="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80",
                performance_rating=4.9,
                location="New York"
            ),
            models.Employee(
                employee_id="EMP-006",
                first_name="Marcus",
                last_name="Aurel",
                email="marcus@company.com",
                phone="+1 (555) 019-7711",
                department_id="PROD",
                department_name="Product Strategy & UI/UX Design",
                job_title="Lead Product Designer",
                role="DEPT_MANAGER",
                hire_date=date(2022, 5, 1),
                salary=130000.0,
                status="ACTIVE",
                skills=json.dumps(["Figma", "Design Systems", "User Research", "Interaction Design"]),
                avatar_url="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80",
                performance_rating=4.8,
                location="Austin HQ"
            ),
            models.Employee(
                employee_id="EMP-007",
                first_name="Jessica",
                last_name="Pearson",
                email="jessica@company.com",
                phone="+1 (555) 019-9944",
                department_id="SALES",
                department_name="Sales & Global Marketing",
                job_title="VP of Global Sales",
                role="DEPT_MANAGER",
                hire_date=date(2021, 4, 12),
                salary=155000.0,
                status="ACTIVE",
                skills=json.dumps(["Enterprise Sales", "B2B Negotiations", "Growth Hacking", "CRM"]),
                avatar_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
                performance_rating=4.7,
                location="Chicago"
            ),
            models.Employee(
                employee_id="EMP-008",
                first_name="Maya",
                last_name="Lin",
                email="maya@company.com",
                phone="+1 (555) 019-4488",
                department_id="ENG",
                department_name="Engineering & Technology",
                job_title="DevOps & Cloud Architect",
                role="EMPLOYEE",
                hire_date=date(2023, 1, 10),
                salary=135000.0,
                status="ON_LEAVE",
                skills=json.dumps(["Kubernetes", "Terraform", "CI/CD", "AWS", "Prometheus"]),
                avatar_url="https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=150&auto=format&fit=crop&q=80",
                manager_id="EMP-003",
                performance_rating=4.6,
                location="Seattle / Remote"
            )
        ]
        db.add_all(seed_data)
        db.commit()
        print("Default employees seeded successfully into Employee DB.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(get_db())
    try:
        seed_default_employees(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Employee Microservice",
    description="Employee Profiles, Lifecycle, Skills & Organizational Directory Service",
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
    return {"status": "healthy", "service": "employee-service", "version": "1.0.0"}

@app.get("/employees")
def list_employees(
    skip: int = 0,
    limit: int = 100,
    department_id: str = Query(None),
    status_filter: str = Query(None, alias="status"),
    search: str = Query(None),
    db: Session = Depends(get_db)
):
    if db.query(models.Employee).count() == 0:
        seed_default_employees(db)

    query = db.query(models.Employee)
    
    if department_id:
        query = query.filter(models.Employee.department_id == department_id)
    if status_filter:
        query = query.filter(models.Employee.status == status_filter)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                models.Employee.first_name.ilike(search_fmt),
                models.Employee.last_name.ilike(search_fmt),
                models.Employee.email.ilike(search_fmt),
                models.Employee.employee_id.ilike(search_fmt),
                models.Employee.job_title.ilike(search_fmt)
            )
        )
    
    employees = query.offset(skip).limit(limit).all()
    return [format_employee_response(e) for e in employees]

@app.get("/employees/stats")
def get_employee_stats(db: Session = Depends(get_db)):
    if db.query(models.Employee).count() == 0:
        seed_default_employees(db)

    total = db.query(models.Employee).count()
    active = db.query(models.Employee).filter(models.Employee.status == "ACTIVE").count()
    on_leave = db.query(models.Employee).filter(models.Employee.status == "ON_LEAVE").count()
    terminated = db.query(models.Employee).filter(models.Employee.status == "TERMINATED").count()
    
    avg_salary = db.query(func.avg(models.Employee.salary)).scalar() or 0.0
    total_payroll = db.query(func.sum(models.Employee.salary)).scalar() or 0.0
    
    dept_counts = (
        db.query(models.Employee.department_id, func.count(models.Employee.id))
        .group_by(models.Employee.department_id)
        .all()
    )
    headcounts = {dept: count for dept, count in dept_counts}

    return {
        "total_employees": total,
        "active_employees": active,
        "on_leave_employees": on_leave,
        "terminated_employees": terminated,
        "avg_salary": round(avg_salary, 2),
        "total_payroll_budget": round(total_payroll, 2),
        "department_headcounts": headcounts
    }

@app.get("/employees/{emp_id}")
def get_employee(emp_id: str, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(
        (models.Employee.id == emp_id) | (models.Employee.employee_id == emp_id)
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return format_employee_response(emp)

@app.post("/employees", status_code=status.HTTP_201_CREATED)
async def create_employee(
    emp_in: schemas.EmployeeCreate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    if db.query(models.Employee).filter(models.Employee.employee_id == emp_in.employee_id).first():
        raise HTTPException(status_code=400, detail="Employee ID already exists")
    if db.query(models.Employee).filter(models.Employee.email == emp_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered for another employee")

    emp_dict = emp_in.model_dump()
    skills_list = emp_dict.pop("skills", [])
    
    new_emp = models.Employee(**emp_dict)
    new_emp.set_skills(skills_list)
    
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    await event_bus.publish(
        event_type="employee.created",
        payload={
            "employee_id": new_emp.employee_id,
            "email": new_emp.email,
            "name": new_emp.full_name,
            "department_id": new_emp.department_id,
            "salary": new_emp.salary
        },
        source_service="employee-service"
    )

    return format_employee_response(new_emp)

@app.put("/employees/{emp_id}")
async def update_employee(
    emp_id: str,
    emp_in: schemas.EmployeeUpdate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER", "DEPT_MANAGER"])),
    db: Session = Depends(get_db)
):
    emp = db.query(models.Employee).filter(
        (models.Employee.id == emp_id) | (models.Employee.employee_id == emp_id)
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = emp_in.model_dump(exclude_unset=True)
    if "skills" in update_data and update_data["skills"] is not None:
        emp.set_skills(update_data.pop("skills"))

    for field, value in update_data.items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)

    await event_bus.publish(
        event_type="employee.updated",
        payload={
            "employee_id": emp.employee_id,
            "department_id": emp.department_id,
            "status": emp.status,
            "salary": emp.salary
        },
        source_service="employee-service"
    )

    return format_employee_response(emp)

@app.delete("/employees/{emp_id}")
async def delete_employee(
    emp_id: str,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    emp = db.query(models.Employee).filter(
        (models.Employee.id == emp_id) | (models.Employee.employee_id == emp_id)
    ).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    deleted_id = emp.employee_id
    db.delete(emp)
    db.commit()

    await event_bus.publish(
        event_type="employee.deleted",
        payload={"employee_id": deleted_id},
        source_service="employee-service"
    )

    return {"message": f"Employee {deleted_id} deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
