"""Add game stats to user

Revision ID: 56d1d4dcef96
Revises: 26059d338e23
Create Date: 2025-06-10 13:48:59.595283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56d1d4dcef96'
down_revision: Union[str, None] = '26059d338e23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # op.add_column('users', sa.Column('coins', sa.Integer(), nullable=True))
    # op.add_column('users', sa.Column('xp', sa.Integer(), nullable=True))
    # op.add_column('users', sa.Column('level', sa.Integer(), nullable=True))
    # op.add_column('users', sa.Column('high_score', sa.Integer(), nullable=True))
    # op.add_column('users', sa.Column('last_daily_claim', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'last_daily_claim')
    op.drop_column('users', 'high_score')
    op.drop_column('users', 'level')
    op.drop_column('users', 'xp')
    op.drop_column('users', 'coins')
    # ### end Alembic commands ###
