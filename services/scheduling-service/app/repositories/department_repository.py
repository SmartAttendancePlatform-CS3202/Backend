from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.identity import Department, AcademicYear

def get_all_departments(db: Session, skip: int = 0, limit: int = 100) -> List[Department]:
    return db.query(Department).offset(skip).limit(limit).all()

def get_department(db: Session, department_id: UUID) -> Optional[Department]:
    return db.query(Department).filter(Department.id == department_id).first()

def create_department(db: Session, data: dict) -> Department:
    db_obj = Department(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_department(db: Session, db_obj: Department, update_data: dict) -> Department:
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_all_academic_years(db: Session, skip: int = 0, limit: int = 100) -> List[AcademicYear]:
    return db.query(AcademicYear).offset(skip).limit(limit).all()

def create_academic_year(db: Session, data: dict) -> AcademicYear:
    db_obj = AcademicYear(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
