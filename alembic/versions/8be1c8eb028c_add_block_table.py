"""add block table

Revision ID: 8be1c8eb028c
Revises: 3538728bdf54
Create Date: 2025-06-12 12:18:25.570185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8be1c8eb028c'
down_revision: Union[str, None] = '3538728bdf54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('blocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('blocker_id', sa.Integer(), nullable=False),
    sa.Column('blocked_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('blocks')
    # ### end Alembic commands ###
