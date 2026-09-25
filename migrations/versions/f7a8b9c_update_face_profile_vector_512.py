"""Update face_profiles embedding column to vector(512) and enrollment_version default to 4

Revision ID: f7a8b9cupdate
Revises: e6f7a8bupdate
Create Date: 2026-09-25 01:40:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f7a8b9cupdate'
down_revision: Union[str, Sequence[str], None] = 'e6f7a8bupdate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing 192D profiles are wiped as all students will re-register on 512D FaceNet
    op.execute(
        """
        TRUNCATE TABLE face_profiles CASCADE;
        ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(512);
        ALTER TABLE face_profiles ALTER COLUMN enrollment_version SET DEFAULT 4;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        TRUNCATE TABLE face_profiles CASCADE;
        ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(192);
        ALTER TABLE face_profiles ALTER COLUMN enrollment_version SET DEFAULT 3;
        """
    )
