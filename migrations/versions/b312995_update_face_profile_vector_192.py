"""Update face_profiles embedding column to vector(192)

Revision ID: b312995update
Revises: a2487db326cd
Create Date: 2026-09-17 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b312995update'
down_revision: Union[str, Sequence[str], None] = 'a2487db326cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(192) USING embedding::vector(192);"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE face_profiles ALTER COLUMN embedding TYPE vector(512) USING embedding::vector(512);"
    )
