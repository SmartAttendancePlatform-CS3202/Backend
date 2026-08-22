from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared_core.models.vision import FaceProfile


def get_active_embedding(db: Session, student_id: str):
    return db.query(FaceProfile).filter(FaceProfile.student_id == UUID(student_id), FaceProfile.is_active.is_(True)).first()


def save_embedding(db: Session, student_id: str, embedding: list[float], reference_photo_url: str, quality_score: float | None = None):
    existing = get_active_embedding(db, student_id)
    if existing:
        existing.is_active = False
        existing.superseded_at = datetime.now(timezone.utc)
    obj = FaceProfile(student_id=UUID(student_id), embedding=embedding, reference_photo_url=reference_photo_url, quality_score=quality_score, is_active=True)
    db.add(obj); db.commit(); db.refresh(obj); return obj
