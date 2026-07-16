"""
Face embedding extraction and matching. Swap in whichever model you
pick (DeepFace/ArcFace, face_recognition/dlib, MediaPipe + a separate
embedding model, etc). Keep the confidence-threshold + retry logic
here so attendance-service stays model-agnostic.
"""
import os

from app.repositories import face_data_repository
from app.services import embedding_service


def _threshold() -> float:
    return float(os.environ.get("FACE_MATCH_THRESHOLD", "0.6"))


def verify(student_id: str, face_image_base64: str) -> dict:
    candidate_embedding = embedding_service.extract_embedding(face_image_base64)
    reference_embedding = face_data_repository.get_active_embedding(student_id)
    confidence = embedding_service.cosine_similarity(candidate_embedding, reference_embedding)
    return {"is_match": confidence >= _threshold(), "confidence": confidence}


def register(student_id: str, face_image_base64: str) -> dict:
    embedding = embedding_service.extract_embedding(face_image_base64)
    face_data_repository.save_embedding(student_id, embedding)
    return {"status": "registered"}
