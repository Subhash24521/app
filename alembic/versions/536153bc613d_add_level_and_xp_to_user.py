"""Add level and xp columns to users"""

from alembic import op
import sqlalchemy as sa

revision = '536153bc613d'
down_revision = None  # or to the actual previous revision ID if known
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('level', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('xp', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('users', 'level')
    op.drop_column('users', 'xp')
