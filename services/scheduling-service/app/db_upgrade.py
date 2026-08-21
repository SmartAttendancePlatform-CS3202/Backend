import sqlalchemy
from sqlalchemy import text
import os

# Use DIRECT_URL since it's a migration/DDL change
DATABASE_URL = os.environ.get("DIRECT_URL", "postgresql://postgres.ywxuyhdvcvfqayckertu:CSE23batch2026@aws-1-ap-south-1.pooler.supabase.com:5432/postgres")

engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE departments ADD COLUMN code VARCHAR;"))
        print("Added 'code' column.")
    except Exception as e:
        print("code column might exist:", e)
        
    try:
        conn.execute(text("ALTER TABLE departments ADD COLUMN faculty_head VARCHAR;"))
        print("Added 'faculty_head' column.")
    except Exception as e:
        print("faculty_head column might exist:", e)
        
    try:
        conn.execute(text("ALTER TABLE departments ADD COLUMN description TEXT;"))
        print("Added 'description' column.")
    except Exception as e:
        print("description column might exist:", e)
        
    conn.commit()
    print("Database upgrade finished.")
