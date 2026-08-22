from uuid import UUID
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from shared_core.models.enums import UserRole, UserStatus

class UserOut(BaseModel):
    id: UUID
    username: str
    role: UserRole
    status: UserStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserRoleUpdate(BaseModel):
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

class StudentOut(UserOut):
    student_index_no: str
    full_name: str
    name_with_initials: str
    display_name: str
    department_id: Optional[UUID] = None
    academic_year_id: Optional[UUID] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nic: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None

class StudentUpdate(BaseModel):
    contact_number: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None

class LecturerOut(UserOut):
    lecturer_code: Optional[str] = None
    department_id: Optional[UUID] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None
