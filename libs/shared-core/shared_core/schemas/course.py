from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CourseBase(BaseModel):
    course_code: str
    name: str
    department_id: Optional[UUID] = None
    credits: Optional[int] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    course_code: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[UUID] = None
    credits: Optional[int] = None

class CourseOut(CourseBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CourseOfferingBase(BaseModel):
    offering_code: Optional[str] = None
    course_id: UUID
    academic_year_id: UUID
    lecturer_id: UUID
    semester: Optional[str] = None
    day: Optional[str] = "Monday"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[UUID] = None
    max_students: Optional[int] = None
    late_threshold_minutes: int = 10
    random_check_enabled: bool = True
    random_check_window_minutes: int = 10
    is_active: bool = True

class CourseOfferingCreate(CourseOfferingBase):
    pass

class CourseOfferingUpdate(BaseModel):
    offering_code: Optional[str] = None
    lecturer_id: Optional[UUID] = None
    semester: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[UUID] = None
    max_students: Optional[int] = None
    late_threshold_minutes: Optional[int] = None
    random_check_enabled: Optional[bool] = None
    random_check_window_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class CourseOfferingOut(CourseOfferingBase):
    id: UUID
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    venue_name: Optional[str] = None
    lecturer_name: Optional[str] = None
    enrolled_count: Optional[int] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
