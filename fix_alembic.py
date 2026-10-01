import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join('services', 'attendance-service', '.env'))
url = os.environ['DATABASE_URL'].replace('?pgbouncer=true', '')

conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("UPDATE alembic_version SET version_num = 'g8b9c0dupdate'")
conn.commit()
print("Updated alembic_version successfully")
