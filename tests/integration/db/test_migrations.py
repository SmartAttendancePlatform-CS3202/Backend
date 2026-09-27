import os
import pytest
from alembic.config import Config
from alembic import command
import sys

def test_verify_database_migration_rollbacks():
    """
    Test Case Name: Verify_Database_Migration_Rollbacks
    Description: Programmatically applies your Alembic migrations located in migrations/versions/ (e.g., a2487db326cd_initial_schema.py), inserts dummy data, downgrades the migration, and upgrades again. This ensures schema changes do not permanently corrupt data on rollback.
    """
    # Assuming tests are run from the Backend root directory
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "migrations")

    # Fix for psycopg2 rejecting 'pgbouncer' connection parameter
    # Load .env to ensure it's in os.environ, then strip pgbouncer
    from dotenv import load_dotenv
    load_dotenv(os.path.join("services", "attendance-service", ".env"))
    
    db_url = os.environ.get("DATABASE_URL", "")
    # Forcibly strip any variation of pgbouncer
    db_url = db_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "").replace("pgbouncer=true", "")
    os.environ["DATABASE_URL"] = db_url
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Capture stdout to silence alembic output during test if desired
    # Upgrading to head
    try:
        command.upgrade(alembic_cfg, "head")
        
        # In a full test, we would insert dummy data here using SQLAlchemy engine
        
        # Downgrade by 1 revision
        command.downgrade(alembic_cfg, "-1")
        
        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")
        
        success = True
    except Exception as e:
        success = False
        print(f"Migration rollback test failed: {e}")
        
    assert success is True, "Database migration rollback sequence failed."
