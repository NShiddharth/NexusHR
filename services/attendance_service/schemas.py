from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime

class AttendanceCheckIn(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    notes: Optional[str] = None

class AttendanceCheckOut(BaseModel):
    employee_id: str
    notes: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: Optional[str] = None
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    total_hours: float
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeaveRequestCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    leave_type: str # ANNUAL, SICK, CASUAL, MATERNITY, UNPAID
    start_date: date
    end_date: date
    reason: str

class LeaveReviewAction(BaseModel):
    status: str # APPROVED, REJECTED
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    review_notes: Optional[str] = None

class LeaveRequestResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days_count: int
    reason: str
    status: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PerformanceReviewCreate(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    reviewer_id: str
    reviewer_name: Optional[str] = None
    period: str
    rating: float
    strengths: Optional[str] = None
    areas_for_growth: Optional[str] = None
    goals_met: bool = True

class PerformanceReviewResponse(PerformanceReviewCreate):
    id: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AttendanceOverview(BaseModel):
    today_present: int
    today_late: int
    today_on_leave: int
    pending_leaves: int
    average_performance: float
    today_on_duty: int = 0


class OnDutyCount(BaseModel):
    """
    Real-time count of employees currently on premises:
    checked in today and NOT yet checked out.
    """
    on_duty_count: int
    as_of: date
