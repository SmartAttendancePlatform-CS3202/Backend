import math
import os
from typing import Any
import numpy as np
from sqlalchemy.orm import Session
from app.repositories import face_data_repository
from app.services import adaptive_learning

EXPECTED_EMBEDDING_DIM = 512
EXPECTED_DEPTH_DIM = 48
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


def _validate_depth_vector(depth_features: list[float] | None) -> np.ndarray:
    if depth_features is None:
        raise ValueError("Depth feature vector must be provided")
    if len(depth_features) != EXPECTED_DEPTH_DIM:
        raise ValueError(
            f"Depth feature dimension mismatch: expected {EXPECTED_DEPTH_DIM}, got {len(depth_features)}"
        )
    arr = np.asarray(depth_features, dtype=np.float64)
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
    enrollment_version: int = 4,
) -> dict[str, Any]:
    valid_centroid = _validate_vector(embedding)

    validated_poses = None
    if pose_embeddings is not None:
        validated_poses = []
        for p in pose_embeddings:
            p_vec = _validate_vector(p)
            validated_poses.append(p_vec.tolist())

    validated_depth = None
    if depth_features is not None:
        validated_depth = _validate_depth_vector(depth_features).tolist()

    reference_photo_url = f"https://storage.example.com/faces/{student_id}.jpg"
    face_data_repository.save_embedding(
        db,
        student_id,
        valid_centroid.tolist(),
        reference_photo_url,
        quality_score=quality_score,
        pose_embeddings=validated_poses,
        depth_features=validated_depth,
        enrollment_metadata=enrollment_metadata,
        enrollment_version=enrollment_version,
    )
    return {
        "status": "success",
        "student_id": student_id,
        "reference_photo_url": reference_photo_url,
        "enrollment_version": enrollment_version,
        "pose_count": len(validated_poses) if validated_poses else 0,
        "has_depth": validated_depth is not None,
        "message": f"Face biometric profile v{enrollment_version} registered successfully.",
    }


def verify_face(
    db: Session,
    student_id: str,
    live_embedding: list[float],
    live_depth_features: list[float] | None = None,
    trigger_adaptive_learning: bool = True,
) -> dict[str, Any]:
    live = _validate_vector(live_embedding)

    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        raise ValueError(f"NO_ACTIVE_PROFILE: No active face profile found for student {student_id}")

    threshold = float(os.environ.get("FACE_SIMILARITY_THRESHOLD", str(DEFAULT_SIMILARITY_THRESHOLD)))

    # Version check: Require modern v4 512D FaceNet embeddings
    raw_version = getattr(profile, "enrollment_version", 4)
    if isinstance(raw_version, (int, float)):
        version = int(raw_version)
    else:
        try:
            version = int(str(raw_version))
        except (ValueError, TypeError):
            version = 4

    if version < 4:
        return {
            "is_match": False,
            "confidence": 0.0,
            "centroid_similarity": 0.0,
            "threshold": threshold,
            "student_id": student_id,
            "requires_re_registration": True,
            "message": "Legacy biometric profile detected. Please re-register your face.",
        }

    ref = np.asarray(profile.embedding, dtype=np.float64)
    if ref.shape[0] != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Stored embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIM}, found {ref.shape[0]}"
        )

    norm_ref = float(np.linalg.norm(ref))
    norm_live = float(np.linalg.norm(live))
    if norm_ref == 0.0 or norm_live == 0.0:
        raise ValueError("DEGENERATE_EMBEDDING: Stored or live embedding has zero norm")

    # Primary: Centroid cosine similarity
    centroid_sim = float(np.dot(ref, live) / (norm_ref * norm_live))
    centroid_sim = max(-1.0, min(1.0, centroid_sim))

    # Secondary: Multi-pose best matching
    best_pose_sim = None
    stored_poses = getattr(profile, "pose_embeddings", None)
    if isinstance(stored_poses, list) and len(stored_poses) > 0:
        sims = []
        for p in stored_poses:
            if isinstance(p, list) and len(p) == EXPECTED_EMBEDDING_DIM:
                p_arr = np.asarray(p, dtype=np.float64)
                p_norm = float(np.linalg.norm(p_arr))
                if p_norm > 0:
                    s = float(np.dot(p_arr, live) / (p_norm * norm_live))
                    sims.append(max(-1.0, min(1.0, s)))
        if sims:
            best_pose_sim = max(sims)

    # Tertiary: Depth topology match (if available in live and profile)
    depth_sim = None
    stored_depth = getattr(profile, "depth_features", None)
    if live_depth_features is not None and isinstance(stored_depth, list) and len(stored_depth) == EXPECTED_DEPTH_DIM:
        try:
            live_depth_arr = _validate_depth_vector(live_depth_features)
            stored_depth_arr = np.asarray(stored_depth, dtype=np.float64)
            dist = float(np.linalg.norm(live_depth_arr - stored_depth_arr))
            depth_sim = float(math.exp(-dist / (math.sqrt(EXPECTED_DEPTH_DIM) * 0.5)))
        except Exception:
            depth_sim = None

    # Identity Confidence: Unskewed facial cosine similarity
    if best_pose_sim is not None:
        confidence = max(centroid_sim, best_pose_sim)
    else:
        confidence = centroid_sim

    # Anti-Spoofing Gate: Reject if 3D pseudo-depth topology fails sanity threshold
    MIN_DEPTH_THRESHOLD = 0.40
    if depth_sim is not None and depth_sim < MIN_DEPTH_THRESHOLD:
        return {
            "is_match": False,
            "confidence": round(confidence, 4),
            "centroid_similarity": round(centroid_sim, 4),
            "best_pose_similarity": round(best_pose_sim, 4) if best_pose_sim is not None else None,
            "depth_similarity": round(depth_sim, 4),
            "threshold": threshold,
            "student_id": student_id,
            "message": "Face liveness/topology verification failed. Please try again.",
        }

    is_match = confidence >= threshold

    # Automated silent adaptive learning
    adaptation_result = None
    if is_match and trigger_adaptive_learning:
        try:
            adaptation_result = adaptive_learning.adapt_centroid_on_success(
                db,
                student_id,
                live_embedding=live.tolist(),
                match_confidence=confidence,
            )
        except Exception:
            pass  # Non-blocking for verification

    result: dict[str, Any] = {
        "is_match": is_match,
        "confidence": round(confidence, 4),
        "centroid_similarity": round(centroid_sim, 4),
        "threshold": threshold,
        "student_id": student_id,
    }
    if best_pose_sim is not None:
        result["best_pose_similarity"] = round(best_pose_sim, 4)
    if depth_sim is not None:
        result["depth_similarity"] = round(depth_sim, 4)
    if adaptation_result and adaptation_result.get("applied"):
        result["adapted"] = True
        result["drift_degrees"] = adaptation_result.get("angular_drift_deg")

    return result

