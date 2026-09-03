from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories import notification_repository

def get_my_notices(db: Session, user_id: UUID): return notification_repository.get_notices(db, user_id)
def get_all_notices(db: Session): return notification_repository.get_all_notices(db)
def broadcast_notice(db: Session, data: dict, creator_id: UUID): return notification_repository.create_notice(db, data, creator_id)
def mark_read(db: Session, notice_id: UUID, user_id: UUID): return notification_repository.mark_read(db, notice_id, user_id)
