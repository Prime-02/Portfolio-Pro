"""fix_notification_type

Revision ID: bf8b93d352d8
Revises: ce8dfe8d9081
Create Date: 2025-06-11 22:24:07.876542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf8b93d352d8'
down_revision: Union[str, None] = 'ce8dfe8d9081'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
