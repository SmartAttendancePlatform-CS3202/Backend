import base64
import numpy as np
import cv2
from deepface import DeepFace

def extract_embedding(image_base64: str) -> list[float]:
    """
    Decodes a base64 image and extracts a 512-dimension face embedding using DeepFace (Facenet512).
    """
    # 1. Decode base64 string to bytes
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]
    img_data = base64.b64decode(image_base64)
    
    # 2. Convert to numpy array and decode image using OpenCV
    np_arr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Failed to decode image")

    # 3. Extract embedding
    # We use Facenet512 to match the Vector(512) requirement
    try:
        results = DeepFace.represent(img_path=img, model_name="Facenet512", enforce_detection=True)
        if not results:
            raise ValueError("No face detected")
        # DeepFace.represent returns a list of dictionaries (one for each face detected)
        embedding = results[0]["embedding"]
        return embedding
    except Exception as e:
        raise ValueError(f"Face extraction failed: {str(e)}")
