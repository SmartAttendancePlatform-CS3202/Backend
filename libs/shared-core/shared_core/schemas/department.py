from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DepartmentBase(BaseModel):
    name: str
    faculty_name: Optional[str] = None
    contact_number: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(DepartmentBase):
    name: Optional[str] = None

class DepartmentOut(DepartmentBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
