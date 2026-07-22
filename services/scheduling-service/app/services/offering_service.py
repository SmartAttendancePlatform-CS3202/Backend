from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import offering_repository

def get_all_offerings(db: Session, skip: int = 0, limit: int = 100):
    return offering_repository.get_all_offerings(db, skip=skip, limit=limit)

def get_offering(db: Session, offering_id: UUID):
    return offering_repository.get_offering(db, offering_id)

def get_offerings_by_course(db: Session, course_id: UUID, skip: int = 0, limit: int = 100):
    return offering_repository.get_offerings_by_course(db, course_id, skip=skip, limit=limit)

def create_offering(db: Session, data: dict, user_id: UUID):
    return offering_repository.create_offering(db, data, user_id)

def update_offering(db: Session, offering_id: UUID, update_data: dict):
    offering = offering_repository.get_offering(db, offering_id)
    if not offering:
        return None
    return offering_repository.update_offering(db, offering, update_data)
