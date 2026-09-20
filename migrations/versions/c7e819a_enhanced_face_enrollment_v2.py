"""Add multi-dimensional biometric enrollment fields to face_profiles

Revision ID: c7e819aupdate
Revises: b312995update
Create Date: 2026-09-20 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7e819aupdate'
down_revision: Union[str, Sequence[str], None] = 'b312995update'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('face_profiles', sa.Column('pose_embeddings', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('face_profiles', sa.Column('depth_features', postgresql.ARRAY(sa.Numeric()), nullable=True))
    op.add_column('face_profiles', sa.Column('enrollment_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('face_profiles', sa.Column('enrollment_version', sa.Integer(), server_default=sa.text('2'), nullable=False))


def downgrade() -> None:
    op.drop_column('face_profiles', 'enrollment_version')
    op.drop_column('face_profiles', 'enrollment_metadata')
    op.drop_column('face_profiles', 'depth_features')
    op.drop_column('face_profiles', 'pose_embeddings')
