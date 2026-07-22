from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class EnrollmentBase(BaseModel):
    student_id: UUID
    course_offering_id: UUID

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentOut(EnrollmentBase):
    id: UUID
    enrolled_at: datetime
    enrolled_by: UUID
    is_active: bool
    unenrolled_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
