from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from shared_core.models.identity import User
from app.routers.checkin import CheckInRequest, RandomCheckRequest
from app.routers.onboarding import RegisterFaceRequest, register_face
from app.services.attendance_service import record_random_check


def test_checkin_request_validation():
    valid_payload = {
        "lecture_session_id": str(uuid4()),
        "latitude": 6.9271,
        "longitude": 79.8612,
        "face_embedding": [0.01] * 512,
    }
    req = CheckInRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 512

    # Test invalid dimension
    with pytest.raises(Exception):
        CheckInRequest.model_validate({**valid_payload, "face_embedding": [0.01] * 100})


def test_random_check_request_validation():
    valid_payload = {
        "lecture_session_id": str(uuid4()),
        "verification_window_id": str(uuid4()),
        "latitude": 6.9271,
        "longitude": 79.8612,
        "face_embedding": [0.01] * 512,
    }
    req = RandomCheckRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 512

    with pytest.raises(Exception):
        RandomCheckRequest.model_validate({**valid_payload, "face_embedding": [0.01] * 50})


@pytest.mark.anyio
async def test_record_random_check_success():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()
    window_id = uuid4()

    from datetime import datetime, timezone
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.status = "ongoing"
    mock_session.scheduled_at = datetime.now(timezone.utc)
    mock_session.duration_mins = 60
    mock_session.course_offering = MagicMock(late_threshold_minutes=10)
    mock_window = MagicMock()
    mock_window.id = window_id

    mock_record = MagicMock()
    mock_record.first_check_in_at = datetime.now(timezone.utc)
    mock_record.is_manually_overridden = False
    mock_record.status = MagicMock(value="present")

    payload = RandomCheckRequest(
        lecture_session_id=session_id,
        verification_window_id=window_id,
        latitude=0.0,
        longitude=0.0,
        face_embedding=[0.02] * 512,
    )

    with patch(
        "app.services.attendance_service._assert_student_enrolled",
        return_value=mock_session,
    ), patch(
        "app.repositories.attendance_repository.get_open_window",
        return_value=mock_window,
    ), patch(
        "app.repositories.attendance_repository.get_attendance_record",
        return_value=mock_record,
    ), patch(
        "app.services.attendance_service._match_student_face",
        return_value=(True, 0.95, 0.70, None, False),
    ), patch(
        "app.services.attendance_service._venue_check",
        return_value=({"inside": True, "distance_meters": 10.0}, {"name": "Test Venue"}),
    ):
        res = await record_random_check(db, student_id, payload)
        assert res["status"] == "success"
        assert "attempt_id" in res


def test_onboarding_register_face_calls_ai_vision_client():
    db = MagicMock()
    student_user = MagicMock(spec=User)
    student_user.id = uuid4()

    req = RegisterFaceRequest(face_embedding=[0.05] * 512, quality_score=0.9)

    with patch(
        "app.clients.ai_vision_client.register_face",
        return_value={"status": "success", "student_id": str(student_user.id)},
    ) as mock_client:
        res = register_face(req, current_user=student_user, db=db)
        assert res["status"] == "success"
        mock_client.assert_called_once_with(
            student_id=str(student_user.id),
            face_embedding=req.face_embedding,
            quality_score=0.9,
            pose_embeddings=None,
            depth_features=None,
            enrollment_metadata=None,
        )
