import os
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from prometheus_client import Counter
from shared_core.auth.rbac import require_role
from shared_core.config import get_settings
from shared_core.models.identity import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
REGISTER_FACE_ATTEMPTS = Counter("register_face_attempt_count", "Face registration attempts", ["reason"])

class RegisterFaceRequest(BaseModel):
    face_image_base64: str = Field(min_length=100, max_length=6_800_000)

@router.post("/register-face")
async def register_face(data: RegisterFaceRequest, current_user: User = Depends(require_role("student"))):
    REGISTER_FACE_ATTEMPTS.labels(reason="attempt").inc()
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{os.environ.get('AI_VISION_SERVICE_URL', 'http://ai-vision-service:8000')}/internal/register",
                json={"student_id": str(current_user.id), "face_image_base64": data.face_image_base64},
                headers={"X-Internal-Key": settings.internal_api_key},
            )
            resp.raise_for_status()
            REGISTER_FACE_ATTEMPTS.labels(reason="success").inc()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
        raise HTTPException(exc.response.status_code, f"Face registration failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
        raise HTTPException(503, "AI Vision service unavailable") from exc
