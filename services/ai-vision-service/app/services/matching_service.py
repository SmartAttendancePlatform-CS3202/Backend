import os
import numpy as np
from sqlalchemy.orm import Session
from app.repositories import face_data_repository

EXPECTED_EMBEDDING_DIM = 192
DEFAULT_SIMILARITY_THRESHOLD = 0.70


def _validate_vector(embedding: list[float] | None) -> np.ndarray:
    if embedding is None:
        raise ValueError("Embedding vector must be provided")
    if len(embedding) != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, got {len(embedding)}"
        )
    arr = np.asarray(embedding, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError("DEGENERATE_EMBEDDING: Vector contains NaN or infinite values")
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        raise ValueError("DEGENERATE_EMBEDDING: Vector has zero magnitude")
    return arr


def register_face(
    db: Session,
    student_id: str,
    embedding: list[float],
    quality_score: float = 1.0,
) -> dict:
    valid_vec = _validate_vector(embedding)
    reference_photo_url = f"https://storage.example.com/faces/{student_id}.jpg"
    face_data_repository.save_embedding(
        db,
        student_id,
        valid_vec.tolist(),
        reference_photo_url,
        quality_score=quality_score,
    )
    return {
        "status": "success",
        "student_id": student_id,
        "reference_photo_url": reference_photo_url,
        "message": f"Face embedding ({EXPECTED_EMBEDDING_DIM}-D) registered successfully.",
    }


def verify_face(
    db: Session,
    student_id: str,
    live_embedding: list[float],
) -> dict:
    live = _validate_vector(live_embedding)

    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        raise ValueError(f"NO_ACTIVE_PROFILE: No active face profile found for student {student_id}")

    ref = np.asarray(profile.embedding, dtype=np.float64)
    if ref.shape[0] != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Stored embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, found {ref.shape[0]}"
        )

    norm_ref = float(np.linalg.norm(ref))
    norm_live = float(np.linalg.norm(live))
    if norm_ref == 0.0 or norm_live == 0.0:
        raise ValueError("DEGENERATE_EMBEDDING: Stored or live embedding has zero norm")

    similarity = float(np.dot(ref, live) / (norm_ref * norm_live))
    # Clip numerical precision drift to [-1.0, 1.0]
    similarity = max(-1.0, min(1.0, similarity))

    threshold = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", str(DEFAULT_SIMILARITY_THRESHOLD)))
    is_match = similarity >= threshold

    return {
        "is_match": is_match,
        "confidence": round(similarity, 4),
        "threshold": threshold,
        "student_id": student_id,
    }
