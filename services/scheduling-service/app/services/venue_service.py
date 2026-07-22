from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import venue_repository

def get_all_venues(db: Session, skip: int = 0, limit: int = 100):
    return venue_repository.get_all_venues(db, skip=skip, limit=limit)

def get_venue(db: Session, venue_id: UUID):
    return venue_repository.get_venue(db, venue_id=venue_id)

def create_venue(db: Session, data: dict):
    return venue_repository.create_venue(db, data=data)

def update_venue(db: Session, venue_id: UUID, update_data: dict):
    venue = venue_repository.get_venue(db, venue_id=venue_id)
    if not venue:
        return None
    return venue_repository.update_venue(db, db_obj=venue, update_data=update_data)
