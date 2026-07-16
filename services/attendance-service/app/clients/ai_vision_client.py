"""HTTP client for ai-vision-service — internal service-to-service call."""
import os

import httpx

from shared_core.config import get_settings


def verify_face(student_id: str, face_image_base64: str) -> dict:
    settings = get_settings()
    base_url = os.environ.get("AI_VISION_SERVICE_URL", "http://ai-vision-service:8000")
    resp = httpx.post(
        f"{base_url}/verify",
        json={"student_id": student_id, "face_image_base64": face_image_base64},
        headers={"X-Internal-Key": settings.internal_api_key},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()
