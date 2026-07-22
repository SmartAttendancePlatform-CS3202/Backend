from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.academic_year import AcademicYearOut, AcademicYearCreate
from shared_core.models.identity import User
from app.services import department_service

router = APIRouter(prefix="/academic-years", tags=["academic-years"])

@router.get("", response_model=List[AcademicYearOut])
def list_academic_years(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return department_service.get_all_academic_years(db, skip=skip, limit=limit)

@router.post("", response_model=AcademicYearOut, status_code=status.HTTP_201_CREATED)
def create_academic_year(
    data: AcademicYearCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return department_service.create_academic_year(db, data.model_dump())
