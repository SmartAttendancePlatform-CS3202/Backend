from pydantic import BaseModel


class CheckInRequest(BaseModel):
    lecture_session_id: str
    latitude: float
    longitude: float


class RandomCheckRequest(BaseModel):
    verification_window_id: str
    latitude: float
    longitude: float
    face_image_base64: str


class LectureSessionOut(BaseModel):
    id: str
    status: str
