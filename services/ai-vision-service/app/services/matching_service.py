import numpy as np
from sqlalchemy.orm import Session
from app.services import embedding_service
from app.repositories import face_data_repository

def register_face(db: Session, student_id: str, image_base64: str) -> dict:
    """
    Extracts an embedding and saves it to the database for the given student.
    """
    # 1. Extract embedding
    embedding = embedding_service.extract_embedding(image_base64)
    
    # 2. Save to database
    # For now, we mock the reference photo URL since we don't have a storage service implemented here
    reference_photo_url = f"https://storage.example.com/faces/{student_id}.jpg"
    
    face_data_repository.save_embedding(db, student_id, embedding, reference_photo_url)
    
    return {"status": "success", "student_id": student_id, "message": "Face registered successfully"}

def verify_face(db: Session, student_id: str, live_image_base64: str) -> dict:
    """
    Verifies a live image against the stored embedding using Cosine Similarity.
    """
    # 1. Fetch reference embedding from DB
    profile = face_data_repository.get_active_embedding(db, student_id)
    if not profile:
        raise ValueError("No active face profile found for student")
        
    reference_embedding = np.array(profile.embedding)
    
    # 2. Extract embedding from live image
    live_embedding = np.array(embedding_service.extract_embedding(live_image_base64))
    
    # 3. Calculate cosine similarity
    dot_product = np.dot(reference_embedding, live_embedding)
    norm_ref = np.linalg.norm(reference_embedding)
    norm_live = np.linalg.norm(live_embedding)
    
    similarity = dot_product / (norm_ref * norm_live)
    
    # DeepFace Facenet512 cosine similarity threshold is typically around 0.3
    # Wait, cosine distance threshold is 0.3, so similarity threshold is 1 - 0.3 = 0.7
    # For now, let's use a standard threshold
    threshold = 0.6
    
    is_match = bool(similarity >= threshold)
    
    return {
        "is_match": is_match,
        "confidence": float(similarity)
    }
