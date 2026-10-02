import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from contextlib import asynccontextmanager

shared_path = Path(__file__).resolve().parent.parent / "shared"
sys.path.append(str(shared_path.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
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

def seed_default_attendance(db: Session):
    if db.query(models.AttendanceRecord).count() == 0:
        today = date.today()
        # Seeded PRESENT employees are currently ON DUTY (check_in set, check_out=None).
        # total_hours is 0.0 because they haven't checked out yet.
        seed_records = [
            models.AttendanceRecord(
                employee_id="EMP-001",
                employee_name="Alexander Vance",
                date=today,
                check_in=datetime.now().replace(hour=8, minute=55, second=0, microsecond=0),
                check_out=None,
                total_hours=0.0,
                status="PRESENT"
            ),
            models.AttendanceRecord(
                employee_id="EMP-002",
                employee_name="Sarah Jenkins",
                date=today,
                check_in=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                check_out=None,
                total_hours=0.0,
                status="PRESENT"
            ),
            models.AttendanceRecord(
                employee_id="EMP-003",
                employee_name="David Chen",
                date=today,
                check_in=datetime.now().replace(hour=9, minute=15, second=0, microsecond=0),
                check_out=None,
                total_hours=0.0,
                status="PRESENT"
            ),
            models.AttendanceRecord(
                employee_id="EMP-004",
                employee_name="Alex Rivera",
                date=today,
                check_in=datetime.now().replace(hour=8, minute=45, second=0, microsecond=0),
                check_out=None,
                total_hours=0.0,
                status="PRESENT"
            ),
            models.AttendanceRecord(
                employee_id="EMP-008",
                employee_name="Maya Lin",
                date=today,
                status="ON_LEAVE",
                notes="Approved Annual Leave"
            ),
        ]
        db.add_all(seed_records)

    if db.query(models.LeaveRequest).count() == 0:
        today = date.today()
        leave_requests = [
            models.LeaveRequest(
                employee_id="EMP-008",
                employee_name="Maya Lin",
                leave_type="ANNUAL",
                start_date=today - timedelta(days=2),
                end_date=today + timedelta(days=5),
                days_count=7,
                reason="Family vacation and wellness trip.",
                status="APPROVED",
                reviewer_id="EMP-002",
                reviewer_name="Sarah Jenkins",
                review_notes="Approved. Enjoy your time off!"
            ),
            models.LeaveRequest(
                employee_id="EMP-004",
                employee_name="Alex Rivera",
                leave_type="CASUAL",
                start_date=today + timedelta(days=10),
                end_date=today + timedelta(days=12),
                days_count=2,
                reason="Attending Tech Conference in Seattle.",
                status="PENDING"
            ),
        ]
        db.add_all(leave_requests)

    if db.query(models.PerformanceReview).count() == 0:
        reviews = [
            models.PerformanceReview(
                employee_id="EMP-004",
                employee_name="Alex Rivera",
                reviewer_id="EMP-003",
                reviewer_name="David Chen",
                period="2026-Q1",
                rating=4.8,
                strengths="Exceptional API development speed, proactive code reviews, great architectural ideas.",
                areas_for_growth="Expand distributed caching benchmarks.",
                goals_met=True
            ),
            models.PerformanceReview(
                employee_id="EMP-008",
                employee_name="Maya Lin",
                reviewer_id="EMP-003",
                reviewer_name="David Chen",
                period="2026-Q1",
                rating=4.7,
                strengths="Automated CI/CD pipeline down from 15m to 3m, robust zero-downtime deployment setups.",
                areas_for_growth="Documentation of disaster recovery playbooks.",
                goals_met=True
            )
        ]
        db.add_all(reviews)
        db.commit()
        print("Default attendance, leaves and reviews seeded successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = next(get_db())
    try:
        seed_default_attendance(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Attendance & Performance Microservice",
    description="Time Tracking, Leave Applications, Approvals & Review Management Service",
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
    return {"status": "healthy", "service": "attendance-service", "version": "1.0.0"}

@app.get("/attendance/overview", response_model=schemas.AttendanceOverview)
def get_overview(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    if db.query(models.AttendanceRecord).count() == 0:
        seed_default_attendance(db)

    today = date.today()
    present_count = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.date == today,
        models.AttendanceRecord.status == "PRESENT"
    ).count()
    
    late_count = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.date == today,
        models.AttendanceRecord.status == "LATE"
    ).count()
    
    leave_count = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.date == today,
        models.AttendanceRecord.status == "ON_LEAVE"
    ).count()

    pending_leaves = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == "PENDING"
    ).count()

    avg_perf = db.query(func.avg(models.PerformanceReview.rating)).scalar() or 4.5

    on_duty_count = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.date == today,
        models.AttendanceRecord.check_in.isnot(None),
        models.AttendanceRecord.check_out.is_(None)
    ).count()

    return {
        "today_present": present_count,
        "today_late": late_count,
        "today_on_leave": leave_count,
        "pending_leaves": pending_leaves,
        "average_performance": round(avg_perf, 2),
        "today_on_duty": on_duty_count
    }

@app.get("/attendance/on-duty/count", response_model=schemas.OnDutyCount)
def get_on_duty_count(response: Response, db: Session = Depends(get_db)):
    """
    Returns the real-time count of employees currently on duty:
    those who have checked in today and have NOT yet checked out.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    if db.query(models.AttendanceRecord).count() == 0:
        seed_default_attendance(db)

    today = date.today()
    on_duty = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.date == today,
        models.AttendanceRecord.check_in.isnot(None),
        models.AttendanceRecord.check_out.is_(None)
    ).count()
    return {"on_duty_count": on_duty, "as_of": today}

@app.get("/attendance", response_model=list[schemas.AttendanceResponse])
def list_attendance(
    employee_id: str = Query(None),
    target_date: date = Query(None, alias="date"),
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if db.query(models.AttendanceRecord).count() == 0:
        seed_default_attendance(db)

    query = db.query(models.AttendanceRecord)
    if employee_id:
        query = query.filter(models.AttendanceRecord.employee_id == employee_id)
    if target_date:
        query = query.filter(models.AttendanceRecord.date == target_date)
    return query.order_by(models.AttendanceRecord.date.desc()).limit(limit).all()

@app.post("/attendance/check-in", response_model=schemas.AttendanceResponse)
def check_in(checkin_data: schemas.AttendanceCheckIn, db: Session = Depends(get_db)):
    today = date.today()
    existing = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.employee_id == checkin_data.employee_id,
        models.AttendanceRecord.date == today
    ).first()

    now = datetime.now()
    if existing:
        if existing.check_in and existing.check_out:
            # Employee has a complete attendance record for today (checked in and out).
            raise HTTPException(
                status_code=400,
                detail="Employee has already completed attendance for today (checked in and out)"
            )
        if existing.check_in and not existing.check_out:
            # Employee is currently checked in but not yet checked out.
            raise HTTPException(
                status_code=400,
                detail="Employee is already checked in for today"
            )
        # Record exists (e.g. ON_LEAVE) but has no check_in yet — allow check-in.
        existing.check_in = now
        existing.status = "PRESENT" if now.hour < 9 or (now.hour == 9 and now.minute <= 30) else "LATE"
        db.commit()
        db.refresh(existing)
        return existing

    status_val = "PRESENT" if now.hour < 9 or (now.hour == 9 and now.minute <= 30) else "LATE"
    record = models.AttendanceRecord(
        employee_id=checkin_data.employee_id,
        employee_name=checkin_data.employee_name,
        date=today,
        check_in=now,
        status=status_val,
        notes=checkin_data.notes
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.post("/attendance/check-out", response_model=schemas.AttendanceResponse)
def check_out(checkout_data: schemas.AttendanceCheckOut, db: Session = Depends(get_db)):
    today = date.today()
    record = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.employee_id == checkout_data.employee_id,
        models.AttendanceRecord.date == today
    ).first()

    if not record or not record.check_in:
        raise HTTPException(status_code=400, detail="No check-in record found for today")

    now = datetime.now()
    record.check_out = now
    
    delta = (now - record.check_in).total_seconds() / 3600.0
    record.total_hours = round(max(0.0, delta), 2)
    if checkout_data.notes:
        record.notes = (record.notes or "") + f" [Out: {checkout_data.notes}]"

    db.commit()
    db.refresh(record)
    return record

# Leaves Endpoints
@app.get("/leaves", response_model=list[schemas.LeaveRequestResponse])
def list_leaves(
    employee_id: str = Query(None),
    status_filter: str = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    if db.query(models.LeaveRequest).count() == 0:
        seed_default_attendance(db)

    query = db.query(models.LeaveRequest)
    if employee_id:
        query = query.filter(models.LeaveRequest.employee_id == employee_id)
    if status_filter:
        query = query.filter(models.LeaveRequest.status == status_filter)
    return query.order_by(models.LeaveRequest.created_at.desc()).all()

@app.post("/leaves", response_model=schemas.LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def apply_leave(leave_in: schemas.LeaveRequestCreate, db: Session = Depends(get_db)):
    delta_days = (leave_in.end_date - leave_in.start_date).days + 1
    if delta_days <= 0:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")

    # Overlapping active leave check
    overlapping = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == leave_in.employee_id,
        models.LeaveRequest.status.in_(["PENDING", "APPROVED"]),
        models.LeaveRequest.start_date <= leave_in.end_date,
        models.LeaveRequest.end_date >= leave_in.start_date
    ).first()

    if overlapping:
        raise HTTPException(
            status_code=400, 
            detail=f"Overlapping leave request already exists from {overlapping.start_date} to {overlapping.end_date}"
        )

    new_leave = models.LeaveRequest(
        employee_id=leave_in.employee_id,
        employee_name=leave_in.employee_name,
        leave_type=leave_in.leave_type,
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        days_count=delta_days,
        reason=leave_in.reason,
        status="PENDING"
    )
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)

    await event_bus.publish(
        event_type="leave.requested",
        payload={"leave_id": new_leave.id, "employee_id": new_leave.employee_id, "days": delta_days},
        source_service="attendance-service"
    )

    return new_leave

@app.put("/leaves/{leave_id}/review", response_model=schemas.LeaveRequestResponse)
async def review_leave(
    leave_id: str,
    action: schemas.LeaveReviewAction,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER", "DEPT_MANAGER"])),
    db: Session = Depends(get_db)
):
    leave = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave.status in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail=f"Leave request is already {leave.status}")

    new_status = action.status.upper()
    if new_status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be APPROVED or REJECTED")

    leave.status = new_status
    leave.reviewer_id = action.reviewer_id
    leave.reviewer_name = action.reviewer_name
    leave.review_notes = action.review_notes
    leave.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(leave)

    await event_bus.publish(
        event_type="leave.reviewed",
        payload={"leave_id": leave.id, "employee_id": leave.employee_id, "status": leave.status},
        source_service="attendance-service"
    )

    return leave

# Reviews Endpoints
@app.get("/reviews", response_model=list[schemas.PerformanceReviewResponse])
def list_reviews(
    employee_id: str = Query(None),
    period: str = Query(None),
    db: Session = Depends(get_db)
):
    if db.query(models.PerformanceReview).count() == 0:
        seed_default_attendance(db)

    query = db.query(models.PerformanceReview)
    if employee_id:
        query = query.filter(models.PerformanceReview.employee_id == employee_id)
    if period:
        query = query.filter(models.PerformanceReview.period == period)
    return query.order_by(models.PerformanceReview.created_at.desc()).all()

@app.post("/reviews", response_model=schemas.PerformanceReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_in: schemas.PerformanceReviewCreate,
    current_user: TokenPayload = Depends(require_roles(["ADMIN", "HR_MANAGER", "DEPT_MANAGER"])),
    db: Session = Depends(get_db)
):
    if review_in.rating < 1.0 or review_in.rating > 5.0:
        raise HTTPException(status_code=400, detail="Rating must be between 1.0 and 5.0")

    new_review = models.PerformanceReview(**review_in.model_dump())
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
