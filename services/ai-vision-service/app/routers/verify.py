from fastapi import APIRouter
from pydantic import BaseModel

from app.services import matching_service

router = APIRouter(tags=["verification"])


class VerifyRequest(BaseModel):
    student_id: str
    face_image_base64: str


class RegisterRequest(BaseModel):
    student_id: str
    face_image_base64: str


@router.post("/verify", dependencies=[Depends(verify_internal_key)])
def verify_face(
    payload: VerifyRequest,
    db: Session = Depends(get_db)
):
    try:
        return matching_service.verify_face(db, payload.student_id, payload.face_image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/register", dependencies=[Depends(verify_internal_key)], status_code=status.HTTP_201_CREATED)
def register_face(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        return matching_service.register_face(db, payload.student_id, payload.face_image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
