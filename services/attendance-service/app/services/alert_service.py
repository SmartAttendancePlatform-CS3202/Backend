from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import alert_repository

def get_alerts(db: Session, skip: int = 0, limit: int = 100):
    return alert_repository.get_alerts(db, skip=skip, limit=limit)

def mark_read(db: Session, alert_id: UUID):
    return alert_repository.mark_read(db, alert_id)
