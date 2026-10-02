import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status
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

def seed_default_departments(db: Session):
    if db.query(models.Department).count() == 0:
        depts = [
            models.Department(
                name="Engineering & Technology",
                code="ENG",
                description="Core software development, cloud infrastructure, AI and DevOps engineering.",
                manager_id="EMP-003",
                manager_name="David Chen",
                budget=1500000.0,
                location="San Francisco / Remote"
            ),
            models.Department(
                name="Human Resources & People Ops",
                code="HR",
                description="Talent acquisition, employee welfare, performance management and organizational culture.",
                manager_id="EMP-002",
                manager_name="Sarah Jenkins",
                budget=450000.0,
                location="Austin HQ"
            ),
            models.Department(
                name="Finance, Accounting & Payroll",
                code="FIN",
                description="Financial auditing, payroll calculations, investments and tax compliance.",
                manager_id="EMP-005",
                manager_name="Elena Rostova",
                budget=600000.0,
                location="New York"
            ),
            models.Department(
                name="Product Strategy & UI/UX Design",
                code="PROD",
                description="Product discovery, user experience research, roadmap design and prototyping.",
                manager_id="EMP-006",
                manager_name="Marcus Aurel",
                budget=750000.0,
                location="Austin HQ"
            ),
            models.Department(
                name="Sales & Global Marketing",
                code="SALES",
                description="Enterprise client acquisition, partner relations and brand marketing campaigns.",
                manager_id="EMP-007",
                manager_name="Jessica Pearson",
                budget=900000.0,
                location="Chicago"
            ),
        ]
        db.add_all(depts)
        db.commit()
        print("Default departments seeded successfully into Department DB.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(get_db())
    try:
        seed_default_departments(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Department Microservice",
    description="Department Lifecycle, Org Structure & Budgeting Service",
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
    return {"status": "healthy", "service": "department-service", "version": "1.0.0"}

@app.get("/departments", response_model=list[schemas.DepartmentResponse])
def list_departments(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    if db.query(models.Department).count() == 0:
        seed_default_departments(db)

    query = db.query(models.Department)
    if active_only:
        query = query.filter(models.Department.is_active == True)
    return query.offset(skip).limit(limit).all()

@app.get("/departments/stats", response_model=schemas.DepartmentStats)
def get_department_stats(db: Session = Depends(get_db)):
    if db.query(models.Department).count() == 0:
        seed_default_departments(db)

    total = db.query(models.Department).count()
    active = db.query(models.Department).filter(models.Department.is_active == True).count()
    total_budget = db.query(func.sum(models.Department.budget)).scalar() or 0.0
    avg_budget = total_budget / total if total > 0 else 0.0
    return {
        "total_departments": total,
        "active_departments": active,
        "total_budget": total_budget,
        "avg_budget_per_dept": round(avg_budget, 2)
    }

@app.get("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
def get_department(dept_id: str, db: Session = Depends(get_db)):
    dept = db.query(models.Department).filter(
        (models.Department.id == dept_id) | (models.Department.code == dept_id)
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept

@app.post("/departments", response_model=schemas.DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept_in: schemas.DepartmentCreate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER"])),
    db: Session = Depends(get_db)
):
    if db.query(models.Department).filter(models.Department.code == dept_in.code).first():
        raise HTTPException(status_code=400, detail=f"Department code '{dept_in.code}' already exists")
    if db.query(models.Department).filter(models.Department.name == dept_in.name).first():
        raise HTTPException(status_code=400, detail=f"Department name '{dept_in.name}' already exists")

    new_dept = models.Department(**dept_in.model_dump())
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)

    await event_bus.publish(
        event_type="department.created",
        payload={"id": new_dept.id, "name": new_dept.name, "code": new_dept.code},
        source_service="department-service"
    )

    return new_dept

@app.put("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
async def update_department(
    dept_id: str,
    dept_in: schemas.DepartmentUpdate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER", "DEPT_MANAGER"])),
    db: Session = Depends(get_db)
):
    dept = db.query(models.Department).filter(models.Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    update_data = dept_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dept, field, value)
    
    db.commit()
    db.refresh(dept)

    await event_bus.publish(
        event_type="department.updated",
        payload={"id": dept.id, "name": dept.name, "code": dept.code},
        source_service="department-service"
    )

    return dept

@app.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: str,
    current_user: TokenPayload = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    dept = db.query(models.Department).filter(
        (models.Department.id == dept_id) | (models.Department.code == dept_id)
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    dept_id_val = dept.id
    db.delete(dept)
    db.commit()

    await event_bus.publish(
        event_type="department.deleted",
        payload={"id": dept_id_val},
        source_service="department-service"
    )

    return {"message": "Department deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
