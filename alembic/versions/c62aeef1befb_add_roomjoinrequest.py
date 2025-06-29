"""add roomjoinrequest

Revision ID: c62aeef1befb
Revises: 92ee31845e25
Create Date: 2025-06-13 12:23:24.886686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c62aeef1befb'
down_revision: Union[str, None] = '92ee31845e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_constraint('room_join_requests_room_id_fkey', 'room_join_requests', type_='foreignkey')
    op.create_foreign_key(
        'room_join_requests_room_id_fkey',
        'room_join_requests',
        'game_rooms',
        ['room_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    op.drop_constraint('room_join_requests_room_id_fkey', 'room_join_requests', type_='foreignkey')
    op.create_foreign_key(
        'room_join_requests_room_id_fkey',
        'room_join_requests',
        'game_rooms',
        ['room_id'],
        ['id']
    )
