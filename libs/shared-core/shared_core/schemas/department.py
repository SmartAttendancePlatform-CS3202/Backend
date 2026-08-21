from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DepartmentBase(BaseModel):
    name: str
    code: Optional[str] = None
    faculty_head: Optional[str] = None
    description: Optional[str] = None
    faculty_name: Optional[str] = None
    contact_number: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    faculty_head: Optional[str] = None
    description: Optional[str] = None
    faculty_name: Optional[str] = None
    contact_number: Optional[str] = None

class DepartmentOut(DepartmentBase):
    id: UUID
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
