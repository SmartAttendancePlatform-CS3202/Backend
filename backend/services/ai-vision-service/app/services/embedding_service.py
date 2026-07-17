"""Model-specific extraction logic. This is the one file you'll rewrite
once you've picked a face-matching library."""
import numpy as np


def extract_embedding(face_image_base64: str) -> np.ndarray:
    raise NotImplementedError("Wire this up to your chosen face embedding model")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
