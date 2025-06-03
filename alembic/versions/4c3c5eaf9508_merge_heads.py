"""merge heads

Revision ID: 4c3c5eaf9508
Revises: 418e858faf3e, 7258c7a3b930
Create Date: 2025-06-02 15:35:35.757584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c3c5eaf9508'
down_revision: Union[str, None] = ('418e858faf3e', '7258c7a3b930')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
