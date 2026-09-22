import os
import sqlalchemy
from sqlalchemy import text

DATABASE_URL = os.environ.get("DIRECT_URL", "postgresql://postgres.ywxuyhdvcvfqayckertu:CSE23batch2026@aws-1-ap-south-1.pooler.supabase.com:5432/postgres")

engine = sqlalchemy.create_engine(DATABASE_URL)

def seed_lecturer(
    user_id: str = "e4a298a0-2f94-49c1-8418-49e088a8f101",
    email: str = "arthur.vance@university.ac.lk",
    lecturer_code: str = "LEC-ENG-4092",
    contact_number: str = "+94 77 123 4567"
):
    with engine.connect() as conn:
        # 1. Insert into users table
        conn.execute(
            text("""
                INSERT INTO users (id, username, role, status, is_active)
                VALUES (:id, :username, 'lecturer', 'active', true)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    is_active = EXCLUDED.is_active;
            """),
            {"id": user_id, "username": email}
        )

        # 2. Insert into lecturers table
        conn.execute(
            text("""
                INSERT INTO lecturers (id, lecturer_code, email, contact_number)
                VALUES (:id, :lecturer_code, :email, :contact_number)
                ON CONFLICT (id) DO UPDATE SET
                    lecturer_code = EXCLUDED.lecturer_code,
                    email = EXCLUDED.email,
                    contact_number = EXCLUDED.contact_number;
            """),
            {"id": user_id, "lecturer_code": lecturer_code, "email": email, "contact_number": contact_number}
        )

        conn.commit()
        print(f"✅ Successfully seeded lecturer profile for {email} ({user_id})")

if __name__ == "__main__":
    seed_lecturer()
