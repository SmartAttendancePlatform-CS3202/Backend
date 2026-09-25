from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared_core.models.vision import FaceProfile


def get_active_embedding(db: Session, student_id: str):
    return db.query(FaceProfile).filter(FaceProfile.student_id == UUID(student_id), FaceProfile.is_active.is_(True)).first()


def save_embedding(
    db: Session,
    student_id: str,
    embedding: list[float],
    reference_photo_url: str,
    quality_score: float | None = None,
    pose_embeddings: list[list[float]] | None = None,
    depth_features: list[float] | None = None,
    enrollment_metadata: dict | None = None,
    enrollment_version: int = 4,
):
    existing = get_active_embedding(db, student_id)
    if existing:
        existing.is_active = False
        existing.superseded_at = datetime.now(timezone.utc)
    obj = FaceProfile(
        student_id=UUID(student_id),
        embedding=embedding,
        pose_embeddings=pose_embeddings,
        depth_features=depth_features,
        enrollment_metadata=enrollment_metadata,
        enrollment_version=enrollment_version,
        reference_photo_url=reference_photo_url,
        quality_score=quality_score,
        is_active=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_centroid(
    db: Session,
    profile_id: UUID,
    new_centroid: list[float],
    metadata_update: dict | None = None,
):
    profile = db.query(FaceProfile).filter(FaceProfile.id == profile_id).first()
    if profile:
        profile.embedding = new_centroid
        if metadata_update:
            meta = dict(profile.enrollment_metadata or {})
            meta.update(metadata_update)
            profile.enrollment_metadata = meta
        db.commit()
        db.refresh(profile)
    return profile

