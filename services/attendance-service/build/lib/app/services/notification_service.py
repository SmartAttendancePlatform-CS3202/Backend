from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import notification_repository

def get_my_notices(db: Session, user_id: UUID):
    return notification_repository.get_notices(db, user_id)

def broadcast_notice(db: Session, data: dict):
    return notification_repository.create_notice(db, data)
