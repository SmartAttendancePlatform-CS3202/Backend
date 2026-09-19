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
        "face_embedding": [0.01] * 192,
    }
    req = CheckInRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 192

    # Test invalid dimension
    with pytest.raises(Exception):
        CheckInRequest.model_validate({**valid_payload, "face_embedding": [0.01] * 100})


def test_random_check_request_validation():
    valid_payload = {
        "lecture_session_id": str(uuid4()),
        "verification_window_id": str(uuid4()),
        "latitude": 6.9271,
        "longitude": 79.8612,
        "face_embedding": [0.01] * 192,
    }
    req = RandomCheckRequest.model_validate(valid_payload)
    assert len(req.face_embedding) == 192

    with pytest.raises(Exception):
        RandomCheckRequest.model_validate({**valid_payload, "face_embedding": [0.01] * 50})


@pytest.mark.anyio
async def test_record_random_check_publishes_task_without_gps_check():
    db = MagicMock()
    student_id = uuid4()
    session_id = uuid4()
    window_id = uuid4()

    mock_session = MagicMock()
    mock_session.id = session_id
    mock_window = MagicMock()
    mock_window.id = window_id

    payload = RandomCheckRequest(
        lecture_session_id=session_id,
        verification_window_id=window_id,
        latitude=0.0,
        longitude=0.0,
        face_embedding=[0.02] * 192,
    )

    with patch(
        "app.services.attendance_service._assert_student_enrolled",
        return_value=mock_session,
    ), patch(
        "app.repositories.attendance_repository.get_open_window",
        return_value=mock_window,
    ), patch(
        "app.services.attendance_service.publish_verification_task",
        new_callable=AsyncMock,
    ) as mock_pub:
        res = await record_random_check(db, student_id, payload)
        assert res["status"] == "processing"
        mock_pub.assert_awaited_once()
        task = mock_pub.call_args[0][0]
        assert task.student_id == student_id
        assert len(task.face_embedding) == 192


def test_onboarding_register_face_calls_ai_vision_client():
    db = MagicMock()
    student_user = MagicMock(spec=User)
    student_user.id = uuid4()

    req = RegisterFaceRequest(face_embedding=[0.05] * 192, quality_score=0.9)

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
        )
