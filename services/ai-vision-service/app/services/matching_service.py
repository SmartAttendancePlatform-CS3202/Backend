import os
import numpy as np
from sqlalchemy.orm import Session
from app.services import embedding_service
from app.repositories import face_data_repository


def register_face(db: Session, student_id: str, image_base64: str | None = None, embedding: list[float] | None = None) -> dict:
    if embedding is not None:
        emb = embedding
        quality = 1.0
    elif image_base64:
        emb = embedding_service.extract_embedding(image_base64)
        quality = embedding_service.estimate_quality(image_base64)
    else:
        raise ValueError("Either embedding or image_base64 must be provided")

    reference_photo_url = f"https://storage.example.com/faces/{student_id}.jpg"
    face_data_repository.save_embedding(db, student_id, emb, reference_photo_url, quality_score=quality)
    return {
        "status": "success",
        "student_id": student_id,
        "reference_photo_url": reference_photo_url,
        "message": f"Face embedding ({len(emb)}-D) registered; raw photo is not stored.",
    }


def verify_face(db: Session, student_id: str, live_image_base64: str | None = None, live_embedding: list[float] | None = None) -> dict:
    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        raise ValueError("No active face profile found for student")
    ref = np.asarray(profile.embedding, dtype=np.float64)
    if live_embedding is not None:
        live = np.asarray(live_embedding, dtype=np.float64)
    elif live_image_base64:
        live = np.asarray(embedding_service.extract_embedding(live_image_base64), dtype=np.float64)
    else:
        raise ValueError("Either live_embedding or live_image_base64 must be provided")

    if ref.shape[0] != live.shape[0]:
        raise ValueError(f"Embedding dimension mismatch: stored is {ref.shape[0]}, live is {live.shape[0]}")

    denom = np.linalg.norm(ref) * np.linalg.norm(live)
    if denom == 0:
        raise ValueError("Invalid face embedding")
    similarity = float(np.dot(ref, live) / denom)
    threshold = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", "0.70"))
    return {"is_match": similarity >= threshold, "confidence": similarity, "threshold": threshold}
