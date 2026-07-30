from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import department_repository

def get_all_departments(db: Session, skip: int = 0, limit: int = 100):
    return department_repository.get_all_departments(db, skip=skip, limit=limit)

def get_department(db: Session, department_id: UUID):
    return department_repository.get_department(db, department_id=department_id)

def create_department(db: Session, data: dict):
    return department_repository.create_department(db, data=data)

def update_department(db: Session, department_id: UUID, update_data: dict):
    dept = department_repository.get_department(db, department_id=department_id)
    if not dept:
        return None
    return department_repository.update_department(db, db_obj=dept, update_data=update_data)

def get_all_academic_years(db: Session, skip: int = 0, limit: int = 100):
    return department_repository.get_all_academic_years(db, skip=skip, limit=limit)

def create_academic_year(db: Session, data: dict):
    return department_repository.create_academic_year(db, data=data)
