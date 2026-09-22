from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.services.adaptive_learning import (
    calculate_centroid_drift,
    adapt_centroid_on_success,
    MIN_CONFIDENCE_FOR_ADAPTATION,
    MAX_ANGULAR_DRIFT_DEGREES,
)


def _make_unit_vector(dim=192, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim)
    return v / np.linalg.norm(v)


def test_calculate_centroid_drift_identical():
    v = _make_unit_vector()
    updated, drift = calculate_centroid_drift(v, v, alpha=0.05)
    assert np.isclose(drift, 0.0, atol=1e-3)
    assert np.allclose(updated, v, atol=1e-3)


def test_calculate_centroid_drift_slight_shift():
    v1 = _make_unit_vector(seed=1)
    v2 = _make_unit_vector(seed=2)
    # v1 and v2 are roughly orthogonal in 192D (~90 deg)
    # With alpha = 0.05, drift should be small (~2.8 - 3.0 degrees)
    updated, drift = calculate_centroid_drift(v1, v2, alpha=0.05)
    assert 0.0 < drift < 5.0
    assert np.isclose(np.linalg.norm(updated), 1.0)


def test_adapt_centroid_low_confidence_rejected():
    db = MagicMock()
    v = _make_unit_vector().tolist()
    res = adapt_centroid_on_success(
        db,
        student_id="11111111-1111-1111-1111-111111111111",
        live_embedding=v,
        match_confidence=0.80,  # Below 0.85
    )
    assert res["applied"] is False
    assert "CONFIDENCE_TOO_LOW" in res["reason"]


def test_adapt_centroid_rate_limited():
    db = MagicMock()
    student_id = "11111111-1111-1111-1111-111111111111"
    v = _make_unit_vector().tolist()

    recent_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    mock_profile = MagicMock()
    mock_profile.embedding = v
    mock_profile.enrollment_metadata = {"last_centroid_update": recent_time}

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        res = adapt_centroid_on_success(
            db,
            student_id=student_id,
            live_embedding=v,
            match_confidence=0.92,
        )
        assert res["applied"] is False
        assert "RATE_LIMITED" in res["reason"]


def test_adapt_centroid_success():
    db = MagicMock()
    student_id = "11111111-1111-1111-1111-111111111111"
    v1 = _make_unit_vector(seed=1)
    v2 = _make_unit_vector(seed=2)

    old_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    mock_profile = MagicMock()
    mock_profile.id = "mock-uuid"
    mock_profile.embedding = v1.tolist()
    mock_profile.enrollment_metadata = {"last_centroid_update": old_time, "adaptation_count": 2}

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        with patch("app.repositories.face_data_repository.update_centroid") as mock_update:
            res = adapt_centroid_on_success(
                db,
                student_id=student_id,
                live_embedding=v2.tolist(),
                match_confidence=0.95,
                alpha=0.05,
            )
            assert res["applied"] is True
            assert res["adaptation_count"] == 3
            assert res["angular_drift_deg"] < MAX_ANGULAR_DRIFT_DEGREES
            mock_update.assert_called_once()
