import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, Text
try:
    from .database import Base
except (ImportError, ValueError):
    from database import Base

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(50), index=True, nullable=False)
    employee_name = Column(String(150), nullable=True)
    date = Column(Date, default=date.today, index=True)
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, default=0.0)
    status = Column(String(50), default="PRESENT")
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(50), index=True, nullable=False)
    employee_name = Column(String(150), nullable=True)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Integer, default=1)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING")
    reviewer_id = Column(String(50), nullable=True)
    reviewer_name = Column(String(150), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String(50), index=True, nullable=False)
    employee_name = Column(String(150), nullable=True)
    reviewer_id = Column(String(50), nullable=False)
    reviewer_name = Column(String(150), nullable=True)
    period = Column(String(50), nullable=False)
    rating = Column(Float, nullable=False)
    strengths = Column(Text, nullable=True)
    areas_for_growth = Column(Text, nullable=True)
    goals_met = Column(Boolean, default=True)
    status = Column(String(50), default="COMPLETED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
