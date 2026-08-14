from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx
import os

from shared_core.auth.jwt import get_current_user
from shared_core.auth.rbac import require_role
from shared_core.models.identity import User
from prometheus_client import Counter

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

REGISTER_FACE_ATTEMPTS = Counter(
    "register_face_attempt_count",
    "Total number of student attempts categorized by status/reason",
    ["reason"]
)

class RegisterFaceRequest(BaseModel):
    face_image_base64: str

@router.post("/register-face")
async def register_face(
    data: RegisterFaceRequest,
    current_user: User = Depends(require_role(["student"]))
):
    # This just proxies to AI Vision Service's /register endpoint
    # Actually, we should probably just let the client call AI Vision Service directly, 
    # but the API spec says it's in attendance-service. Let's proxy it.
    base_url = os.environ.get("AI_VISION_SERVICE_URL", "http://ai-vision-service:8000")
    
    # Internal service API key
    from shared_core.config import get_settings
    settings = get_settings()
    
    REGISTER_FACE_ATTEMPTS.labels(reason="attempts").inc()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/register",
                json={
                    "student_id": str(current_user.id),
                    "face_image_base64": data.face_image_base64
                },
                headers={"X-Internal-Key": settings.internal_api_key},
                timeout=30.0
            )
            resp.raise_for_status()
            REGISTER_FACE_ATTEMPTS.labels(reason="success").inc()
            return resp.json()
    except httpx.HTTPError as e:
        REGISTER_FACE_ATTEMPTS.labels(reason="failed").inc()
        raise HTTPException(status_code=500, detail=f"Failed to register face: {str(e)}")
