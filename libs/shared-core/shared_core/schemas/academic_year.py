from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class AcademicYearBase(BaseModel):
    year_level: int
    name: str
    description: Optional[str] = None
    is_active: bool = True

class AcademicYearCreate(AcademicYearBase):
    pass

class AcademicYearUpdate(AcademicYearBase):
    year_level: Optional[int] = None
    name: Optional[str] = None

class AcademicYearOut(AcademicYearBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
