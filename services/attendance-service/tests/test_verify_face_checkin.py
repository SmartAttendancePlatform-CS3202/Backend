from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from shared_core.auth.jwt import get_current_user
from shared_core.db.session import get_db
from shared_core.models.identity import User
from shared_core.models.vision import FaceProfile
from app.main import app
from app.routers.checkin import VerifyFaceRequest
from app.services import attendance_service
from app.services.attendance_service import verify_face_and_record_attendance



@pytest.fixture
def client():
    test_user = MagicMock(spec=User)
    test_user.id = uuid4()
    test_user.role = "student"

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app), test_user.id
    app.dependency_overrides.clear()



def test_verify_face_request_validation():
    valid_payload = {
        "lecture_session_id": "TEST_MOCK_CLASS",
        "latitude": 6.9271,
        "longitude": 79.8612,
        "face_embedding": [0.05] * 512,
    }
    req = VerifyFaceRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 512
    assert req.lecture_session_id == "TEST_MOCK_CLASS"

    # Test invalid dimension
    with pytest.raises(Exception):
        VerifyFaceRequest.model_validate({**valid_payload, "face_embedding": [0.05] * 100})


def test_verify_face_no_registered_profile():
    db = MagicMock()
    student_id = uuid4()

    # Query returns None for FaceProfile
    db.query.return_value.filter.return_value.first.return_value = None

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        face_embedding=[0.05] * 512,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert res["is_match"] is False
    assert "No active face biometric profile" in res["message"]


def test_verify_face_matching_success():
    db = MagicMock()
    student_id = uuid4()

    # Mock matching profile: identical embedding
    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is True
    assert res["is_match"] is True
    assert res["confidence"] >= 0.70
    assert "Face verified successfully" in res["message"]


def test_verify_face_mismatch_failure():
    db = MagicMock()
    student_id = uuid4()

    # Orthogonal / inverse embedding to simulate different person
    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [1.0] * 256 + [0.0] * 256
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    # Live face has opposite coordinates
    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.0] * 256 + [1.0] * 256,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert res["is_match"] is False
    assert res["confidence"] < 0.70
    assert "Face verification failed: Biometric mismatch" in res["message"]


def test_verify_face_outside_geofence_rejected():
    db = MagicMock()
    student_id = uuid4()

    # Face is an exact match!
    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    # Student attempts check-in ~2.7 km away from Moratuwa Seminar Room
    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=6.8200,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert res["is_match"] is True  # Biometrics matched
    assert "Location verification failed: Outside 30m geofence" in res["message"]
    # Verify no AttendanceRecord was added to the database
    db.add.assert_not_called()


def test_verify_face_missing_gps_rejected():
    db = MagicMock()
    student_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=None,
        longitude=None,
        face_embedding=[0.05] * 512,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert "Location verification failed: Missing GPS coordinates" in res["message"]
    db.add.assert_not_called()


def test_router_verify_location_endpoint(client):
    test_client, student_id = client

    # 1. Within 30m of mock venue
    res_inside = test_client.post("/checkin/verify-location", json={
        "lecture_session_id": "TEST_MOCK_CLASS",
        "latitude": 6.7951,
        "longitude": 79.9009,
    })
    assert res_inside.status_code == 200
    data_inside = res_inside.json()
    assert data_inside["inside"] is True
    assert data_inside["distance_meters"] <= 30.0

    # 2. Outside 30m
    res_outside = test_client.post("/checkin/verify-location", json={
        "lecture_session_id": "TEST_MOCK_CLASS",
        "latitude": 6.8200,
        "longitude": 79.9009,
    })
    assert res_outside.status_code == 200
    data_outside = res_outside.json()
    assert data_outside["inside"] is False
    assert data_outside["distance_meters"] > 30.0


def test_router_verify_face_endpoint(client):
    test_client, student_id = client
    payload = {
        "lecture_session_id": "TEST_MOCK_CLASS",
        "latitude": 6.7951,
        "longitude": 79.9009,

        "face_embedding": [0.05] * 512,
    }

    with patch(
        "app.services.attendance_service.verify_face_and_record_attendance",
        return_value={"success": True, "is_match": True, "confidence": 0.95, "message": "Face verified successfully"},
    ):
        res = test_client.post("/checkin/verify-face", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["is_match"] is True


def test_router_active_windows_test_mock_class(client):
    test_client, _ = client
    res = test_client.get("/checkin/windows/active?lecture_session_id=TEST_MOCK_CLASS")
    assert res.status_code == 200
    data = res.json()
    assert data["check_in_window"] is not None
    assert data["check_in_window"]["is_active"] is True


def test_verify_face_legacy_enrollment_version_rejected():
    db = MagicMock()
    student_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None
    mock_profile.enrollment_version = 3  # Legacy version < 4

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    with patch("app.services.attendance_service.ai_vision_client.verify_face", side_effect=Exception("Service offline")):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert res["is_match"] is False
        assert res["requires_re_registration"] is True
        assert "outdated model version" in res["message"]


def test_verify_face_spoofed_depth_rejected():
    db = MagicMock()
    student_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = [1.0] * 24 + [0.0] * 24
    mock_profile.enrollment_version = 4

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
        depth_features=[0.0] * 24 + [1.0] * 24,  # Orthogonal depth (spoof attempt)
    )

    with patch("app.services.attendance_service.ai_vision_client.verify_face", side_effect=Exception("Service offline")):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert res["is_match"] is False
        assert "surface topology check failed" in res["message"]

