"""Merge heads

Revision ID: 7258c7a3b930
Revises: 536153bc613d, f22fadf018dd
Create Date: 2025-06-02 15:21:57.366819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7258c7a3b930'
down_revision: Union[str, None] = ('536153bc613d', 'f22fadf018dd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
