"""Update face_profiles embedding column to vector(192)

Revision ID: e6f7a8bupdate
Revises: d4e5f6aupdate
Create Date: 2026-09-24 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e6f7a8bupdate'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6aupdate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_profiles 
        ALTER COLUMN embedding TYPE vector(192) 
        USING (
            CASE 
                WHEN vector_dims(embedding) = 192 THEN embedding 
                WHEN vector_dims(embedding) > 192 THEN ('[' || array_to_string((string_to_array(trim(both '[]' from embedding::text), ','))[1:192], ',') || ']')::vector(192)
                ELSE (rtrim(embedding::text, ']') || ',' || array_to_string(array_fill(0, ARRAY[192 - vector_dims(embedding)]), ',') || ']')::vector(192)
            END
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_profiles 
        ALTER COLUMN embedding TYPE vector(512) 
        USING (
            CASE 
                WHEN vector_dims(embedding) = 512 THEN embedding 
                WHEN vector_dims(embedding) > 512 THEN ('[' || array_to_string((string_to_array(trim(both '[]' from embedding::text), ','))[1:512], ',') || ']')::vector(512)
                ELSE (rtrim(embedding::text, ']') || ',' || array_to_string(array_fill(0, ARRAY[512 - vector_dims(embedding)]), ',') || ']')::vector(512)
            END
        );
        """
    )
