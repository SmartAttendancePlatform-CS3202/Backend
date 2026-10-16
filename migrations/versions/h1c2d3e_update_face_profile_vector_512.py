"""Update face_profiles embedding column to vector(512)

Revision ID: h1c2d3eupdate
Revises: g8b9c0dupdate
Create Date: 2026-10-01 16:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'h1c2d3eupdate'
down_revision: Union[str, Sequence[str], None] = 'g8b9c0dupdate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Truncate to clean invalid 192D data per migration plan
    op.execute("TRUNCATE TABLE face_profiles CASCADE;")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(512);")


def downgrade() -> None:
    # Reverting back to 192D
    op.execute("TRUNCATE TABLE face_profiles CASCADE;")
    op.execute("ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(192);")
