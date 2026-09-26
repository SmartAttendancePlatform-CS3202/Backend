from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.services.matching_service import (
    EXPECTED_EMBEDDING_DIM,
    register_face,
    verify_face,
    _normalize_vector,
)


def _make_unit_vector(dim=512, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim)
    return (v / np.linalg.norm(v)).tolist()


def test_validate_vector_valid():
    vec = _make_unit_vector(512)
    arr = _normalize_vector(vec, 512, "Embedding")
    assert arr.shape == (512,)
    assert np.isclose(np.linalg.norm(arr), 1.0)


def test_validate_vector_wrong_dimension():
    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        _normalize_vector([0.1] * 128, 512, "Embedding")

    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        _normalize_vector([0.1] * 192, 512, "Embedding")


def test_validate_vector_none():
    with pytest.raises(ValueError, match="Embedding vector must be provided"):
        _normalize_vector(None, 512, "Embedding")


def test_validate_vector_zero_magnitude():
    with pytest.raises(ValueError, match="zero magnitude"):
        _normalize_vector([0.0] * 512, 512, "Embedding")


def test_validate_vector_nan_or_inf():
    vec = [0.1] * 512
    vec[10] = float("nan")
    with pytest.raises(ValueError, match="NaN or infinite"):
        _normalize_vector(vec, 512, "Embedding")


def test_verify_face_identical_match():
    db = MagicMock()
    student_id = "11111111-1111-1111-1111-111111111111"
    vec = _make_unit_vector(512, seed=1)

    mock_profile = MagicMock()
    mock_profile.embedding = vec
    mock_profile.enrollment_version = 5
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        result = verify_face(db, student_id, vec)
        assert result["is_match"] is True
        assert np.isclose(result["confidence"], 1.0, atol=1e-3)
        assert result["student_id"] == student_id


def test_verify_face_different_person_mismatch():
    db = MagicMock()
    student_id = "11111111-1111-1111-1111-111111111111"
    ref_vec = _make_unit_vector(512, seed=10)
    # Generate orthogonal or opposite vector
    diff_vec = (-np.array(ref_vec)).tolist()

    mock_profile = MagicMock()
    mock_profile.embedding = ref_vec
    mock_profile.enrollment_version = 5
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        result = verify_face(db, student_id, diff_vec)
        assert result["is_match"] is False
        assert result["confidence"] <= 0.0


def test_verify_face_no_active_profile():
    db = MagicMock()
    student_id = "22222222-2222-2222-2222-222222222222"
    vec = _make_unit_vector(512)

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=None):
        with pytest.raises(ValueError, match="NO_ACTIVE_PROFILE"):
            verify_face(db, student_id, vec)


def test_register_face():
    db = MagicMock()
    student_id = "33333333-3333-3333-3333-333333333333"
    vec = _make_unit_vector(512)

    with patch("app.repositories.face_data_repository.save_embedding") as mock_save:
        res = register_face(db, student_id, vec, quality_score=0.95)
        assert res["status"] == "success"
        assert res["student_id"] == student_id
        assert res["enrollment_version"] == 5
        mock_save.assert_called_once()


def test_verify_face_legacy_version_rejected():
    db = MagicMock()
    student_id = "44444444-4444-4444-4444-444444444444"
    vec = _make_unit_vector(512)

    mock_profile = MagicMock()
    mock_profile.embedding = vec
    mock_profile.enrollment_version = 4  # Legacy version < 5

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        result = verify_face(db, student_id, vec)
        assert result["is_match"] is False
        assert result["requires_re_registration"] is True
        assert "Major biometric upgrade detected" in result["message"]


def test_verify_face_depth_anti_spoof_gate():
    db = MagicMock()
    student_id = "55555555-5555-5555-5555-555555555555"
    vec = _make_unit_vector(512)

    mock_profile = MagicMock()
    mock_profile.embedding = vec
    mock_profile.enrollment_version = 5
    mock_profile.pose_embeddings = None
    # Stored depth is all zeros
    mock_profile.depth_features = [0.0] * 48

    # Live depth is completely divergent (spoof topology)
    live_depth = [10.0] * 48

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        result = verify_face(db, student_id, vec, live_depth_features=live_depth)
        assert result["is_match"] is False
        assert "topology verification failed" in result["message"]

