"""Update face_profiles embedding column to vector(512)

Revision ID: d4e5f6aupdate
Revises: c7e819aupdate
Create Date: 2026-09-24 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6aupdate'
down_revision: Union[str, Sequence[str], None] = 'c7e819aupdate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_profiles 
        ALTER COLUMN embedding TYPE vector(512) 
        USING (
            CASE 
                WHEN vector_dims(embedding) = 512 THEN embedding 
                ELSE (rtrim(embedding::text, ']') || ',' || array_to_string(array_fill(0, ARRAY[512 - vector_dims(embedding)]), ',') || ']')::vector(512)
            END
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_profiles 
        ALTER COLUMN embedding TYPE vector(192) 
        USING (
            CASE 
                WHEN vector_dims(embedding) = 192 THEN embedding 
                ELSE (rtrim(embedding::text, ']') || ',' || array_to_string(array_fill(0, ARRAY[192 - vector_dims(embedding)]), ',') || ']')::vector(192)
            END
        );
        """
    )
