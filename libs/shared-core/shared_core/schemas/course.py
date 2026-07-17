from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CourseOut(BaseModel):
    id: UUID
    course_code: str
    name: str
    department_id: Optional[UUID] = None
    credits: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CourseOfferingOut(BaseModel):
    id: UUID
    offering_code: Optional[str] = None
    course_id: UUID
    academic_year_id: UUID
    lecturer_id: UUID
    semester: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[UUID] = None
    max_students: Optional[int] = None
    late_threshold_minutes: int
    random_check_enabled: bool
    random_check_window_minutes: int
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
