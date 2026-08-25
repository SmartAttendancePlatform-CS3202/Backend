import os
import numpy as np
from sqlalchemy.orm import Session
from app.services import embedding_service
from app.repositories import face_data_repository


def register_face(db: Session, student_id: str, image_base64: str) -> dict:
    embedding = embedding_service.extract_embedding(image_base64)
    quality = embedding_service.estimate_quality(image_base64)
    reference_photo_url = f"https://storage.example.com/faces/{student_id}.jpg"  # Intentionally fake for now; raw images are not stored.
    face_data_repository.save_embedding(db, student_id, embedding, reference_photo_url, quality_score=quality)
    return {"status": "success", "student_id": student_id, "reference_photo_url": reference_photo_url, "message": "Face embedding registered; raw photo is not stored."}


def verify_face(db: Session, student_id: str, live_image_base64: str) -> dict:
    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile: raise ValueError("No active face profile found for student")
    ref = np.asarray(profile.embedding, dtype=np.float64)
    live = np.asarray(embedding_service.extract_embedding(live_image_base64), dtype=np.float64)
    denom = np.linalg.norm(ref) * np.linalg.norm(live)
    if denom == 0: raise ValueError("Invalid face embedding")
    similarity = float(np.dot(ref, live) / denom)
    threshold = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", "0.70"))
    return {"is_match": similarity >= threshold, "confidence": similarity, "threshold": threshold}
