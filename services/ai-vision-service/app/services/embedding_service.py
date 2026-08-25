import base64, binascii
import numpy as np
import cv2
from deepface import DeepFace

MAX_IMAGE_BYTES = 5_000_000


def _decode_image(image_base64: str):
    raw = image_base64.split(',',1)[1] if ',' in image_base64 else image_base64
    try: data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc: raise ValueError("Invalid base64 image") from exc
    if len(data) > MAX_IMAGE_BYTES: raise ValueError("Image exceeds 5 MB")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None: raise ValueError("Invalid image data")
    return img


def extract_embedding(image_base64: str) -> list[float]:
    img = _decode_image(image_base64)
    try:
        results = DeepFace.represent(img_path=img, model_name="Facenet512", enforce_detection=True)
    except Exception as exc:
        raise ValueError(f"Face extraction failed: {exc}") from exc
    if not results: raise ValueError("No face detected")
    embedding = results[0]["embedding"]
    if len(embedding) != 512: raise ValueError("Unexpected embedding dimension")
    return [float(x) for x in embedding]


def estimate_quality(image_base64: str) -> float:
    img = _decode_image(image_base64)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Lightweight sharpness proxy. Normalized only for storage/diagnostics.
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return min(1.0, variance / 500.0)
