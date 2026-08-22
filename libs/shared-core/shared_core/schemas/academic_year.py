from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AcademicYearBase(BaseModel):
    year_level: int
    name: str

class AcademicYearCreate(AcademicYearBase): pass
class AcademicYearUpdate(BaseModel):
    year_level: int | None = None
    name: str | None = None

class AcademicYearOut(AcademicYearBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
