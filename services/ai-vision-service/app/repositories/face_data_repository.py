from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from shared_core.models.vision import FaceProfile
from datetime import datetime

def get_active_embedding(db: Session, student_id: str) -> Optional[FaceProfile]:
    return db.query(FaceProfile).filter(
        FaceProfile.student_id == student_id,
        FaceProfile.is_active == True
    ).first()

def save_embedding(db: Session, student_id: str, embedding: list[float], reference_photo_url: str):
    # Deactivate existing
    existing = get_active_embedding(db, student_id)
    if existing:
        existing.is_active = False
        existing.superseded_at = datetime.utcnow()
        db.add(existing)

    new_profile = FaceProfile(
        student_id=student_id,
        embedding=embedding,
        reference_photo_url=reference_photo_url,
        is_active=True
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile
