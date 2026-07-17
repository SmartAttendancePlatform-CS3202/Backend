"""Data-access layer for face_profiles (see
university_attendance_schema.sql — uses the pgvector `embedding` column)."""
import numpy as np


def get_active_embedding(student_id: str) -> np.ndarray:
    raise NotImplementedError


def save_embedding(student_id: str, embedding: np.ndarray) -> None:
    raise NotImplementedError
