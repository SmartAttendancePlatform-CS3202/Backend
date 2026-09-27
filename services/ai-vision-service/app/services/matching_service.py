import math
import os
from typing import Any
import numpy as np
from sqlalchemy.orm import Session
from app.repositories import face_data_repository
from app.services import adaptive_learning

EXPECTED_EMBEDDING_DIM = 512
EXPECTED_DEPTH_DIM = 48
DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", 0.70))
ADAPTIVE_LEARNING_THRESHOLD = float(os.environ.get("FACE_ADAPTIVE_THRESHOLD", 0.88))
MIN_DEPTH_THRESHOLD = 0.40


def _normalize_vector(vec: list[float] | None, expected_dim: int, name: str) -> np.ndarray:
    if vec is None:
        raise ValueError(f"{name} vector must be provided")
    if len(vec) != expected_dim:
        raise ValueError(f"{name} dimension mismatch: expected {expected_dim}, got {len(vec)}")
    
    arr = np.asarray(vec, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"DEGENERATE_{name.upper()}: Vector contains NaN or infinite values")
    
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        raise ValueError(f"DEGENERATE_{name.upper()}: Vector has zero magnitude")
        
    return arr / norm


def verify_face(
    db: Session,
    student_id: str,
    live_embedding: list[float],
    live_depth_features: list[float] | None = None,
    trigger_adaptive_learning: bool = True,
) -> dict[str, Any]:
    # 1. Normalize probe vector
    live = _normalize_vector(live_embedding, EXPECTED_EMBEDDING_DIM, "Embedding")

    # 2. Retrieve reference profile
    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        raise ValueError(f"NO_ACTIVE_PROFILE: No active face profile found for student {student_id}")

    if getattr(profile, "enrollment_version", 4) < 5:
        return {
            "is_match": False,
            "confidence": 0.0,
            "student_id": student_id,
            "requires_re_registration": True,
            "message": "Major biometric upgrade detected (Affine Alignment). Please re-register your face.",
        }

    # 3. Centroid Cosine Similarity (Dot product on pre-normalized vectors)
    ref = np.asarray(profile.embedding, dtype=np.float32)
    ref = _normalize_vector(ref.tolist(), EXPECTED_EMBEDDING_DIM, "Profile Embedding")
    centroid_sim = float(np.clip(np.dot(ref, live), -1.0, 1.0))

    # 4. Vectorized Multi-Pose Check
    best_pose_sim = None
    stored_poses = getattr(profile, "pose_embeddings", None)
    if stored_poses:
        poses_matrix = np.asarray(stored_poses, dtype=np.float32)
        if poses_matrix.ndim == 2 and poses_matrix.shape[1] == EXPECTED_EMBEDDING_DIM:
            norms = np.linalg.norm(poses_matrix, axis=1, keepdims=True)
            poses_matrix = np.divide(poses_matrix, norms, out=np.zeros_like(poses_matrix), where=norms!=0)
            sims = np.clip(poses_matrix @ live, -1.0, 1.0)
            best_pose_sim = float(np.max(sims))

    confidence = max(centroid_sim, best_pose_sim) if best_pose_sim is not None else centroid_sim

    # 5. Enforce Depth / Liveness Check if registered
    stored_depth = getattr(profile, "depth_features", None)
    depth_sim = None
    if stored_depth is not None:
        if live_depth_features is None:
            return {
                "is_match": False,
                "confidence": round(confidence, 4),
                "threshold": DEFAULT_SIMILARITY_THRESHOLD,
                "student_id": student_id,
                "message": "Depth validation missing: 3D face verification is required.",
            }
        
        live_depth_arr = np.asarray(live_depth_features, dtype=np.float32)
        stored_depth_arr = np.asarray(stored_depth, dtype=np.float32)
        dist = float(np.linalg.norm(live_depth_arr - stored_depth_arr))
        depth_sim = float(math.exp(-dist / (math.sqrt(EXPECTED_DEPTH_DIM) * 0.5)))

        if depth_sim < MIN_DEPTH_THRESHOLD:
            return {
                "is_match": False,
                "confidence": round(confidence, 4),
                "depth_similarity": round(depth_sim, 4),
                "threshold": DEFAULT_SIMILARITY_THRESHOLD,
                "student_id": student_id,
                "message": "Face liveness/topology verification failed. Please try again.",
            }

    # 6. Final Decision Gate
    is_match = confidence >= DEFAULT_SIMILARITY_THRESHOLD

    # 7. Safe Adaptive Learning (Strict Threshold Guard)
    adaptation_result = None
    if is_match and trigger_adaptive_learning and confidence >= ADAPTIVE_LEARNING_THRESHOLD:
        try:
            adaptation_result = adaptive_learning.adapt_centroid_on_success(
                db,
                student_id,
                live_embedding=live.tolist(),
                match_confidence=confidence,
            )
        except Exception:
            pass

    response: dict[str, Any] = {
        "is_match": is_match,
        "confidence": round(confidence, 4),
        "centroid_similarity": round(centroid_sim, 4),
        "threshold": DEFAULT_SIMILARITY_THRESHOLD,
        "student_id": student_id,
    }
    if best_pose_sim is not None:
        response["best_pose_similarity"] = round(best_pose_sim, 4)
    if depth_sim is not None:
        response["depth_similarity"] = round(depth_sim, 4)
    if adaptation_result and adaptation_result.get("applied"):
        response["adapted"] = True
        response["drift_degrees"] = adaptation_result.get("angular_drift_deg")

    return response


def _validate_depth_vector(vec: list[float] | None) -> np.ndarray:
    if vec is None:
        raise ValueError("Depth feature vector must be provided")
    if len(vec) != EXPECTED_DEPTH_DIM:
        raise ValueError(f"Depth feature dimension mismatch: expected {EXPECTED_DEPTH_DIM}, got {len(vec)}")
    
    arr = np.asarray(vec, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise ValueError("DEGENERATE_DEPTH: Vector contains NaN or infinite values")
    
    return arr


def register_face(
    db: Session,
    student_id: str,
    embedding: list[float],
    quality_score: float = 1.0,
    pose_embeddings: list[list[float]] | None = None,
    depth_features: list[float] | None = None,
    enrollment_metadata: dict | None = None,
    enrollment_version: int = 5,
) -> dict[str, Any]:
    norm_embed = _normalize_vector(embedding, EXPECTED_EMBEDDING_DIM, "Embedding").tolist()
    
    norm_poses = None
    if pose_embeddings:
        norm_poses = []
        for pose in pose_embeddings:
            norm_poses.append(_normalize_vector(pose, EXPECTED_EMBEDDING_DIM, "Pose Embedding").tolist())
    norm_depth = None
    if depth_features:
        norm_depth = _validate_depth_vector(depth_features).tolist()
            
    face_data_repository.save_embedding(
        db=db,
        student_id=student_id,
        embedding=norm_embed,
        reference_photo_url="",
        quality_score=quality_score,
        pose_embeddings=norm_poses,
        depth_features=norm_depth,
        enrollment_metadata=enrollment_metadata,
        enrollment_version=enrollment_version,
    )
    
    response = {
        "status": "success",
        "student_id": student_id,
        "enrollment_version": enrollment_version,
    }
    
    if pose_embeddings:
        response["pose_count"] = len(pose_embeddings)
    if depth_features:
        response["has_depth"] = True
        
    return response