from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from shared_core.auth.rbac import verify_internal_key
from shared_core.db.session import get_db
from app.main import app

client = TestClient(app)

app.dependency_overrides[verify_internal_key] = lambda: True
app.dependency_overrides[get_db] = lambda: MagicMock()


def test_internal_verify_router_success():
    payload = {
        "student_id": "11111111-1111-1111-1111-111111111111",
        "face_embedding": [0.05] * 512,
    }
    with patch(
        "app.services.matching_service.verify_face",
        return_value={"is_match": True, "confidence": 0.98, "threshold": 0.70, "student_id": payload["student_id"]},
    ):
        res = client.post("/internal/verify", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["is_match"] is True
        assert data["confidence"] == 0.98


def test_internal_verify_router_dimension_error():
    payload = {
        "student_id": "11111111-1111-1111-1111-111111111111",
        "face_embedding": [0.05] * 100,  # Invalid dimension
    }
    res = client.post("/internal/verify", json=payload)
    assert res.status_code == 422  # Pydantic validation error


def test_internal_register_router_success():
    payload = {
        "student_id": "11111111-1111-1111-1111-111111111111",
        "face_embedding": [0.05] * 512,
        "quality_score": 1.0,
    }
    with patch(
        "app.services.matching_service.register_face",
        return_value={"status": "success", "student_id": payload["student_id"], "message": "registered"},
    ):
        res = client.post("/internal/register", json=payload)
        assert res.status_code == 201
        assert res.json()["status"] == "success"
