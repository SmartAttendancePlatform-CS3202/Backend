"""Update face_profiles embedding column to vector(192) for MobileFaceNet and enrollment_version default to 5

Revision ID: g8b9c0dupdate
Revises: f7a8b9cupdate
Create Date: 2026-09-30 14:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'g8b9c0dupdate'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9cupdate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We must delete all existing records since 512D cannot be converted to 192D
    op.execute("DELETE FROM face_profiles;")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(192);")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN enrollment_version SET DEFAULT 5;")


def downgrade() -> None:
    # Reverting back to 512D
    op.execute("DELETE FROM face_profiles;")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(512);")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN enrollment_version SET DEFAULT 4;")
