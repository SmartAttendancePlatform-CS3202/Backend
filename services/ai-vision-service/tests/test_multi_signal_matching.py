from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.services.matching_service import (
    register_face,
    verify_face,
    _validate_depth_vector,
)


def _make_unit_vector(dim=512, seed=42):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim)
    return (v / np.linalg.norm(v)).tolist()


def test_validate_depth_vector():
    valid = [0.5] * 48
    arr = _validate_depth_vector(valid)
    assert arr.shape == (48,)

    with pytest.raises(ValueError, match="Depth feature vector must be provided"):
        _validate_depth_vector(None)

    with pytest.raises(ValueError, match="Depth feature dimension mismatch"):
        _validate_depth_vector([0.5] * 32)

    with pytest.raises(ValueError, match="DEGENERATE_DEPTH"):
        bad = [0.5] * 48
        bad[5] = float("nan")
        _validate_depth_vector(bad)


def test_register_face_v2_with_poses_and_depth():
    db = MagicMock()
    student_id = "44444444-4444-4444-4444-444444444444"
    centroid = _make_unit_vector(seed=1)
    poses = [_make_unit_vector(seed=i) for i in range(2, 7)]  # 5 poses
    depth = [0.2] * 48
    metadata = {"capture_duration_ms": 9500}

    with patch("app.repositories.face_data_repository.save_embedding") as mock_save:
        res = register_face(
            db,
            student_id=student_id,
            embedding=centroid,
            quality_score=0.98,
            pose_embeddings=poses,
            depth_features=depth,
            enrollment_metadata=metadata,
            enrollment_version=4,
        )
        assert res["status"] == "success"
        assert res["enrollment_version"] == 4
        assert res["pose_count"] == 5
        assert res["has_depth"] is True
        mock_save.assert_called_once()
        args, kwargs = mock_save.call_args
        assert kwargs["pose_embeddings"] == poses
        assert kwargs["depth_features"] == depth
        assert kwargs["enrollment_version"] == 4


def test_verify_face_with_pose_matching():
    db = MagicMock()
    student_id = "55555555-5555-5555-5555-555555555555"

    centroid = _make_unit_vector(seed=1)
    # Simulate a realistic left turn: correlated with centroid (~0.85 similarity)
    noise = np.array(_make_unit_vector(seed=10))
    perturbed = np.array(centroid) + 0.35 * noise
    left_pose = (perturbed / np.linalg.norm(perturbed)).tolist()
    poses = [centroid, left_pose, _make_unit_vector(seed=11)]

    mock_profile = MagicMock()
    mock_profile.embedding = centroid
    mock_profile.enrollment_version = 4
    mock_profile.pose_embeddings = poses
    mock_profile.depth_features = None

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        # Live vector is close to left_pose
        result = verify_face(
            db,
            student_id,
            live_embedding=left_pose,
            trigger_adaptive_learning=False,
        )
        assert "best_pose_similarity" in result
        assert np.isclose(result["best_pose_similarity"], 1.0, atol=1e-3)
        # Weighted confidence: 0.6 * centroid_sim + 0.4 * best_pose_sim
        assert result["is_match"] is True



def test_verify_face_with_depth_match():
    db = MagicMock()
    student_id = "66666666-6666-6666-6666-666666666666"

    centroid = _make_unit_vector(seed=1)
    poses = [centroid]
    depth = [0.5] * 48

    mock_profile = MagicMock()
    mock_profile.embedding = centroid
    mock_profile.enrollment_version = 4
    mock_profile.pose_embeddings = poses
    mock_profile.depth_features = depth

    with patch("app.repositories.face_data_repository.get_active_embedding", return_value=mock_profile):
        result = verify_face(
            db,
            student_id,
            live_embedding=centroid,
            live_depth_features=depth,
            trigger_adaptive_learning=False,
        )
        assert "depth_similarity" in result
        assert np.isclose(result["depth_similarity"], 1.0, atol=1e-2)
        assert result["is_match"] is True
