"""Adaptive Continuous Learning Service for Face Biometrics.

Safely updates the stored centroid embedding after successful high-confidence verifications
using an Exponential Moving Average (EMA) drift mechanism.
"""
from datetime import datetime, timezone, timedelta
import math
import numpy as np
from sqlalchemy.orm import Session
from app.repositories import face_data_repository

MIN_CONFIDENCE_FOR_ADAPTATION = 0.85
MAX_ANGULAR_DRIFT_DEGREES = 15.0
DEFAULT_ALPHA = 0.05
MIN_UPDATE_INTERVAL_HOURS = 24


def calculate_centroid_drift(
    stored_centroid: np.ndarray,
    live_embedding: np.ndarray,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[np.ndarray, float]:
    """Computes EMA updated centroid and angular drift in degrees.
    
    Formula:
        new_vector = (1 - alpha) * stored + alpha * live
        normalized_new = new_vector / ||new_vector||
    """
    stored_norm = np.linalg.norm(stored_centroid)
    live_norm = np.linalg.norm(live_embedding)
    if stored_norm == 0.0 or live_norm == 0.0:
        raise ValueError("Cannot calculate drift on zero-magnitude embedding")

    s_unit = stored_centroid / stored_norm
    l_unit = live_embedding / live_norm

    new_centroid = (1.0 - alpha) * s_unit + alpha * l_unit
    new_norm = np.linalg.norm(new_centroid)
    if new_norm == 0.0:
        raise ValueError("Updated centroid resulted in zero norm")
    new_unit = new_centroid / new_norm

    # Angular drift between stored and new centroid
    cos_sim = float(np.dot(s_unit, new_unit))
    cos_sim = max(-1.0, min(1.0, cos_sim))
    angular_drift_deg = math.degrees(math.acos(cos_sim))

    return new_unit, round(angular_drift_deg, 4)


def adapt_centroid_on_success(
    db: Session,
    student_id: str,
    live_embedding: list[float],
    match_confidence: float,
    alpha: float = DEFAULT_ALPHA,
) -> dict:
    """Evaluates safety criteria and applies centroid adaptation if eligible."""
    if match_confidence < MIN_CONFIDENCE_FOR_ADAPTATION:
        return {
            "applied": False,
            "reason": f"CONFIDENCE_TOO_LOW: {match_confidence} < {MIN_CONFIDENCE_FOR_ADAPTATION}",
        }

    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        return {"applied": False, "reason": "NO_ACTIVE_PROFILE"}

    metadata = dict(profile.enrollment_metadata or {})
    last_update_str = metadata.get("last_centroid_update")
    now = datetime.now(timezone.utc)

    if last_update_str:
        try:
            last_update = datetime.fromisoformat(last_update_str)
            if now - last_update < timedelta(hours=MIN_UPDATE_INTERVAL_HOURS):
                return {
                    "applied": False,
                    "reason": f"RATE_LIMITED: Last adapted at {last_update_str}",
                }
        except (ValueError, TypeError):
            pass

    stored_arr = np.asarray(profile.embedding, dtype=np.float64)
    live_arr = np.asarray(live_embedding, dtype=np.float64)

    try:
        new_centroid, drift_deg = calculate_centroid_drift(stored_arr, live_arr, alpha=alpha)
    except ValueError as exc:
        return {"applied": False, "reason": str(exc)}

    if drift_deg > MAX_ANGULAR_DRIFT_DEGREES:
        return {
            "applied": False,
            "reason": f"DRIFT_EXCEEDS_CAP: {drift_deg} deg > {MAX_ANGULAR_DRIFT_DEGREES} deg",
        }

    metadata["last_centroid_update"] = now.isoformat()
    metadata["adaptation_count"] = metadata.get("adaptation_count", 0) + 1
    metadata["last_drift_deg"] = drift_deg

    face_data_repository.update_centroid(
        db,
        profile.id,
        new_centroid=new_centroid.tolist(),
        metadata_update=metadata,
    )

    return {
        "applied": True,
        "angular_drift_deg": drift_deg,
        "adaptation_count": metadata["adaptation_count"],
    }
