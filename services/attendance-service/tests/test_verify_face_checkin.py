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
        "face_embedding": [0.05] * 192,
    }
    req = VerifyFaceRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 192
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
        face_embedding=[0.05] * 192,
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
    mock_profile.embedding = [0.05] * 192
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        face_embedding=[0.05] * 192,
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
    mock_profile.embedding = [1.0] * 96 + [0.0] * 96
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    # Live face has opposite coordinates
    payload = VerifyFaceRequest(
        lecture_session_id="TEST_MOCK_CLASS",
        face_embedding=[0.0] * 96 + [1.0] * 96,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert res["is_match"] is False
    assert res["confidence"] < 0.70
    assert "Face verification failed: Biometric mismatch" in res["message"]


def test_router_verify_face_endpoint(client):
    test_client, student_id = client
    payload = {
        "lecture_session_id": "TEST_MOCK_CLASS",
        "face_embedding": [0.05] * 192,
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
