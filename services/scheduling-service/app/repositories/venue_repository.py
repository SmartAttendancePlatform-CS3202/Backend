from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from shared_core.models.attendance import Venue

def get_all_venues(db: Session, skip: int = 0, limit: int = 100) -> List[Venue]:
    return db.query(Venue).offset(skip).limit(limit).all()

def get_venue(db: Session, venue_id: UUID) -> Optional[Venue]:
    return db.query(Venue).filter(Venue.id == venue_id).first()

def create_venue(db: Session, data: dict) -> Venue:
    db_obj = Venue(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_venue(db: Session, db_obj: Venue, update_data: dict) -> Venue:
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj
