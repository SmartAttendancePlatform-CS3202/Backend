from uuid import UUID
from typing import List, Dict, Any
from pydantic import BaseModel

class StudentAttendanceDetail(BaseModel):
    student_id: UUID
    status: str
    first_check_in_at: str | None = None
    random_check_completed_at: str | None = None
    flag_reason: str | None = None

class OfferingReport(BaseModel):
    course_offering_id: UUID
    attendance_percentage: float
    absentee_list: List[StudentAttendanceDetail]
    late_arrival_list: List[StudentAttendanceDetail]

class TrendDataPoint(BaseModel):
    date: str
    attendance_percentage: float

class TrendData(BaseModel):
    course_offering_id: UUID
    trends: List[TrendDataPoint]

class StudentSummary(BaseModel):
    student_id: UUID
    overall_attendance_percentage: float
    course_breakdown: Dict[str, float]

class WeeklyTrendItem(BaseModel):
    week: str
    attendance_rate: float
    total_students: int
