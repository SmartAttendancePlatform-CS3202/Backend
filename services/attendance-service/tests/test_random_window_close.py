from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from shared_core.auth.jwt import get_current_user
from shared_core.db.session import get_db
from shared_core.models.identity import User
from shared_core.models.attendance import LectureSession, VerificationWindow
from shared_core.models.enums import WindowType
from app.main import app
from app.repositories import attendance_repository
from app.services import attendance_service


@pytest.fixture
def lecturer_client():
    test_user = MagicMock(spec=User)
    test_user.id = uuid4()
    test_user.role = "lecturer"

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app), test_user
    app.dependency_overrides.clear()


def test_repository_close_random_window_deactivates():
    db = MagicMock()
    session_id = uuid4()
    
    mock_window = VerificationWindow(
        lecture_session_id=session_id,
        window_type=WindowType.random_check,
        scheduled_open_at=datetime.now(timezone.utc),
        scheduled_close_at=datetime.now(timezone.utc),
        actual_opened_at=datetime.now(timezone.utc),
        is_active=True,
    )
    
    db.query.return_value.filter.return_value.all.return_value = [mock_window]
    
    res = attendance_repository.close_random_window(db, session_id)
    assert res is mock_window
    assert mock_window.is_active is False
    assert mock_window.actual_closed_at is not None
    assert db.commit.called


def test_service_close_random_window_success():
    db = MagicMock()
    session_id = uuid4()
    lecturer_id = uuid4()
    
    current_user = MagicMock()
    current_user.id = lecturer_id
    current_user.role = "lecturer"
    
    mock_session = MagicMock(spec=LectureSession)
    mock_session.id = session_id
    mock_session.course_offering.lecturer_id = lecturer_id
    
    mock_window = MagicMock(spec=VerificationWindow)
    mock_window.id = uuid4()
    mock_window.is_active = False
    
    with patch("app.repositories.attendance_repository.get_session", return_value=mock_session), \
         patch("app.repositories.attendance_repository.close_random_window", return_value=mock_window):
        res = attendance_service.close_random_window(db, session_id, current_user)
        assert res is mock_window


def test_service_close_random_window_forbidden_lecturer():
    db = MagicMock()
    session_id = uuid4()
    
    current_user = MagicMock()
    current_user.id = uuid4()
    current_user.role = "lecturer"
    
    mock_session = MagicMock(spec=LectureSession)
    mock_session.id = session_id
    mock_session.course_offering.lecturer_id = uuid4()  # different lecturer
    
    with patch("app.repositories.attendance_repository.get_session", return_value=mock_session):
        with pytest.raises(HTTPException) as exc:
            attendance_service.close_random_window(db, session_id, current_user)
        assert exc.value.status_code == 403


def test_router_close_random_window_endpoints(lecturer_client):
    test_client, lecturer = lecturer_client
    session_id = uuid4()
    window_id = uuid4()
    
    mock_window = MagicMock()
    mock_window.id = window_id
    mock_window.is_active = False
    
    with patch("app.services.attendance_service.close_random_window", return_value=mock_window):
        res = test_client.post(f"/sessions/{session_id}/windows/random/close")
        assert res.status_code == 200
        assert res.json()["message"] == "Random window closed successfully"
        assert res.json()["window_id"] == str(window_id)

        res_end = test_client.post(f"/sessions/{session_id}/windows/random/end")
        assert res_end.status_code == 200
        assert res_end.json()["message"] == "Random window closed successfully"
        assert res_end.json()["window_id"] == str(window_id)
