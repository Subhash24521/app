"""add coins and last_daily_claim to user"""

from alembic import op
import sqlalchemy as sa

# --- Add this block ---
revision = '418e858faf3e'
down_revision = None # ✅ REPLACE THIS with the actual previous revision ID
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('coins', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('last_daily_claim', sa.DateTime(), nullable=True))
    op.alter_column('users', 'coins', server_default=None)

def downgrade():
    op.drop_column('users', 'last_daily_claim')
    op.drop_column('users', 'coins')
