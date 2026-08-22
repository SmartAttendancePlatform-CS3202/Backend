from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import venue_repository

def get_all_venues(db: Session, skip: int = 0, limit: int = 100):
    return venue_repository.get_all_venues(db, skip=skip, limit=limit)

def get_venue(db: Session, venue_id: UUID):
    return venue_repository.get_venue(db, venue_id=venue_id)

def _normalize_shape(data: dict) -> dict:
    data = dict(data)
    if data.get("shape_type") == "square":
        data["shape_type"] = "polygon"
    return data

def create_venue(db: Session, data: dict):
    return venue_repository.create_venue(db, data=_normalize_shape(data))

def update_venue(db: Session, venue_id: UUID, update_data: dict):
    venue = venue_repository.get_venue(db, venue_id=venue_id)
    if not venue:
        return None
    return venue_repository.update_venue(db, db_obj=venue, update_data=_normalize_shape(update_data))
