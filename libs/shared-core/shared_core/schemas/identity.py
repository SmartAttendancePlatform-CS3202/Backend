from uuid import UUID
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from shared_core.models.enums import UserRole, UserStatus

class UserOut(BaseModel):
    id: UUID
    # NOTE: the `users` table (public.users) does not store email — it lives only on
    # Supabase's auth.users. Until that's synced/joined in, this is best-effort and
    # will be null for records built from the local `users` table alone.
    email: Optional[str] = None
    role: UserRole
    status: UserStatus
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
    # The ORM column is `lecturer_code`, not `employee_id` — the frontend's Lecturer
    # type expects `employee_id`, so we map it here via validation_alias rather than
    # renaming the DB column.
    employee_id: Optional[str] = Field(default=None, validation_alias="lecturer_code")
    full_name: str
    name_with_initials: str
    display_name: str
    department_id: Optional[UUID] = None
    contact_number: Optional[str] = None
    photo_url: Optional[str] = None


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