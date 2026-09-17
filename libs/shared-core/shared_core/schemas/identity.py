from uuid import UUID
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
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
    display_name: Optional[str] = None
    department_id: Optional[UUID] = None
    identifier: Optional[str] = None

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
    department_name: Optional[str] = None
    academic_year_name: Optional[str] = None

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


class StudentRegistrationRequest(BaseModel):
    email: str = Field(..., description="Student email (username)")
    password: str = Field(..., min_length=6, description="Initial password")
    student_index_no: str
    full_name: str
    name_with_initials: str
    display_name: str
    department_id: UUID
    academic_year_id: UUID
    date_of_birth: date
    gender: str
    nic: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None


class UserDirectoryOut(BaseModel):
    """Flattened admin-directory view of a user: base account fields plus
    whichever profile (student/lecturer) applies. Used by GET /users."""

    id: UUID
    email: Optional[str] = None
    role: UserRole
    status: UserStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    identifier: Optional[str] = None  # student index no. or lecturer employee code
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)