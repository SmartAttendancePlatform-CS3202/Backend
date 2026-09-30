from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from shared_core.schemas.events import FaceVerificationTask
from app.rabbitmq.consumer import _handle


@pytest.mark.anyio
async def test_consumer_handle_success():
    task = FaceVerificationTask(
        event_id=uuid4(),
        attempt_id=uuid4(),
        student_id=uuid4(),
        verification_window_id=uuid4(),
        face_embedding=[0.05] * 192,
        latitude=6.9271,
        longitude=79.8612,
    )
    message = MagicMock()
    message.body = task.model_dump_json().encode()
    message.channel = AsyncMock()
    message.ack = AsyncMock()
    message.headers = {}

    mock_db = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_db)

    with patch(
        "app.rabbitmq.consumer.get_session_factory",
        return_value=mock_session_factory,
    ), patch(
        "app.services.matching_service.verify_face",
        return_value={"is_match": True, "confidence": 0.95, "threshold": 0.70, "student_id": str(task.student_id)},
    ), patch("app.rabbitmq.consumer._publish_result", new_callable=AsyncMock) as mock_pub:
        await _handle(message)
        message.ack.assert_awaited_once()
        mock_pub.assert_awaited_once()
        result_payload = mock_pub.call_args[0][1]
        assert result_payload.face_match is True
        assert result_payload.confidence == 0.95
        assert result_payload.status == "completed"


@pytest.mark.anyio
async def test_consumer_handle_no_profile_error():
    task = FaceVerificationTask(
        event_id=uuid4(),
        attempt_id=uuid4(),
        student_id=uuid4(),
        verification_window_id=uuid4(),
        face_embedding=[0.05] * 192,
        latitude=6.9271,
        longitude=79.8612,
    )
    message = MagicMock()
    message.body = task.model_dump_json().encode()
    message.channel = AsyncMock()
    message.ack = AsyncMock()
    message.headers = {}

    mock_db = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_db)

    with patch(
        "app.rabbitmq.consumer.get_session_factory",
        return_value=mock_session_factory,
    ), patch(
        "app.services.matching_service.verify_face",
        side_effect=ValueError("NO_ACTIVE_PROFILE: No active face profile found"),
    ), patch("app.rabbitmq.consumer._publish_result", new_callable=AsyncMock) as mock_pub:
        await _handle(message)
        message.ack.assert_awaited_once()
        mock_pub.assert_awaited_once()
        result_payload = mock_pub.call_args[0][1]
        assert result_payload.face_match is False
        assert result_payload.status == "failed"
        assert "NO_ACTIVE_PROFILE" in result_payload.failure_reason
