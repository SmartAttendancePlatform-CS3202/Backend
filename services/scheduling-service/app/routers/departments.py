from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from shared_core.database.connection import get_db
from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.schemas.department import DepartmentOut, DepartmentCreate, DepartmentUpdate
from shared_core.models.identity import User
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])

@router.get("", response_model=List[DepartmentOut])
def list_departments(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return department_service.get_all_departments(db, skip=skip, limit=limit)

@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    return department_service.create_department(db, data.model_dump())

@router.patch("/{id}", response_model=DepartmentOut)
def update_department(
    id: UUID,
    data: DepartmentUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    dept = department_service.update_department(db, id, data.model_dump(exclude_unset=True))
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept
