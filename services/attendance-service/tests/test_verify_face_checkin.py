from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from shared_core.auth.jwt import get_current_user
from shared_core.db.session import get_db
from shared_core.models.identity import User
from shared_core.models.vision import FaceProfile
from app.main import app
from app.routers.checkin import VerifyFaceRequest
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
    session_id = str(uuid4())
    valid_payload = {
        "lecture_session_id": session_id,
        "latitude": 6.9271,
        "longitude": 79.8612,
        "face_embedding": [0.05] * 512,
    }
    req = VerifyFaceRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 512
    assert req.lecture_session_id == session_id

    # Test invalid dimension
    with pytest.raises(Exception):
        VerifyFaceRequest.model_validate({**valid_payload, "face_embedding": [0.05] * 100})


def test_verify_face_no_registered_profile():
    db = MagicMock()
    student_id = uuid4()

    # Query returns None for FaceProfile
    db.query.return_value.filter.return_value.first.return_value = None

    payload = VerifyFaceRequest(
        lecture_session_id=str(uuid4()),
        face_embedding=[0.05] * 512,
    )

    res = verify_face_and_record_attendance(db, student_id, payload)
    assert res["success"] is False
    assert res["is_match"] is False
    assert "No active face biometric profile" in res["message"]


def test_verify_face_matching_success():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    def mock_query(model):
        q = MagicMock()
        if model == FaceProfile:
            q.filter.return_value.first.return_value = mock_profile
        else:
            q.filter.return_value.first.return_value = None
        return q
    db.query.side_effect = mock_query

    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.course_offering = MagicMock(random_check_enabled=False, late_threshold_minutes=10)
    mock_session.scheduled_at = datetime.now(timezone.utc)
    mock_session.duration_mins = 60

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    with patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": True, "distance_meters": 10.0}, {"name": "CSE Seminar Room"}),
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is True
        assert res["is_match"] is True
        assert res["confidence"] >= 0.70
        assert "Face verified successfully" in res["message"]


def test_verify_face_dual_verification_pending():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    def mock_query(model):
        q = MagicMock()
        if model == FaceProfile:
            q.filter.return_value.first.return_value = mock_profile
        else:
            q.filter.return_value.first.return_value = None
        return q
    db.query.side_effect = mock_query

    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.course_offering = MagicMock(random_check_enabled=True, late_threshold_minutes=10)
    mock_session.scheduled_at = datetime.now(timezone.utc)
    mock_session.duration_mins = 60

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    with patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": True, "distance_meters": 10.0}, {"name": "CSE Seminar Room"}),
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is True
        assert res["is_match"] is True
        assert res["verified_initial"] is True
        assert res["attendance_marked"] is False
        assert res["status"] == "pending_random_check"


def test_verify_face_mismatch_failure():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [1.0] * 256 + [0.0] * 256
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    mock_session = MagicMock()
    mock_session.id = session_id

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.0] * 256 + [1.0] * 256,
    )

    with patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": True, "distance_meters": 10.0}, {"name": "CSE Seminar Room"}),
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert res["is_match"] is False
        assert res["confidence"] < 0.70
        assert "Face verification failed: Biometric mismatch" in res["message"]


def test_verify_face_outside_geofence_rejected():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    mock_session = MagicMock()
    mock_session.id = session_id

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=6.8200,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
    )

    with patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": False, "distance_meters": 2700.0}, {"name": "CSE Seminar Room"}),
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert res["is_match"] is True
        assert "Location verification failed: Outside geofence" in res["message"]


def test_verify_face_missing_gps_rejected():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    mock_session = MagicMock()
    mock_session.id = session_id

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=None,
        longitude=None,
        face_embedding=[0.05] * 512,
    )

    with patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert "Location verification failed: Missing GPS coordinates" in res["message"]


def test_router_verify_location_endpoint(client):
    test_client, student_id = client
    session_id = str(uuid4())

    with patch(
        "app.services.attendance_service.verify_location_precheck",
        side_effect=lambda db, sid, payload: {
            "success": True,
            "inside": payload.latitude == 6.7951,
            "distance_meters": 10.0 if payload.latitude == 6.7951 else 2700.0,
            "radius_meters": 30.0,
            "venue_name": "CSE Seminar Room",
            "lecture_session_id": payload.lecture_session_id,
            "message": "Within geofence" if payload.latitude == 6.7951 else "Outside geofence",
        },
    ):
        res_inside = test_client.post("/checkin/verify-location", json={
            "lecture_session_id": session_id,
            "latitude": 6.7951,
            "longitude": 79.9009,
        })
        assert res_inside.status_code == 200
        assert res_inside.json()["inside"] is True

        res_outside = test_client.post("/checkin/verify-location", json={
            "lecture_session_id": session_id,
            "latitude": 6.8200,
            "longitude": 79.9009,
        })
        assert res_outside.status_code == 200
        assert res_outside.json()["inside"] is False


def test_router_verify_face_endpoint(client):
    test_client, student_id = client
    session_id = str(uuid4())
    payload = {
        "lecture_session_id": session_id,
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


def test_router_active_windows_invalid_format_and_valid_session(client):
    test_client, _ = client
    # 1. Non-UUID string should be rejected with 400
    res_invalid = test_client.get("/checkin/windows/active?lecture_session_id=TEST_MOCK_CLASS")
    assert res_invalid.status_code == 400
    assert "Invalid lecture session ID format" in res_invalid.json()["detail"]

    # 2. Valid UUID should call attendance_service.get_active_windows
    valid_uuid = str(uuid4())
    mock_window_data = {
        "check_in_window": {"id": str(uuid4()), "is_active": True},
        "random_check_active": False,
        "random_check_window": None,
        "venue_geofence": {"venue_name": "CSE Seminar Room"},
        "lecture_session_id": valid_uuid,
    }
    with patch("app.services.attendance_service.get_active_windows", return_value=mock_window_data):
        res_valid = test_client.get(f"/checkin/windows/active?lecture_session_id={valid_uuid}")
        assert res_valid.status_code == 200
        assert res_valid.json()["check_in_window"]["is_active"] is True


def test_verify_face_legacy_enrollment_version_rejected():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = None
    mock_profile.enrollment_version = 3

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
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
    session_id = uuid4()

    mock_profile = MagicMock(spec=FaceProfile)
    mock_profile.embedding = [0.05] * 512
    mock_profile.pose_embeddings = None
    mock_profile.depth_features = [1.0] * 24 + [0.0] * 24
    mock_profile.enrollment_version = 4

    db.query.return_value.filter.return_value.first.return_value = mock_profile

    mock_session = MagicMock()
    mock_session.id = session_id

    payload = VerifyFaceRequest(
        lecture_session_id=str(session_id),
        latitude=6.7951,
        longitude=79.9009,
        face_embedding=[0.05] * 512,
        depth_features=[0.0] * 24 + [1.0] * 24,
    )

    with patch(
        "app.services.attendance_service.ai_vision_client.verify_face",
        side_effect=Exception("Service offline"),
    ), patch(
        "app.services.attendance_service.resolve_session",
        return_value=mock_session,
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": True, "distance_meters": 10.0}, {"name": "CSE Seminar Room"}),
    ):
        res = verify_face_and_record_attendance(db, student_id, payload)
        assert res["success"] is False
        assert res["is_match"] is False
        assert "surface topology check failed" in res["message"]
