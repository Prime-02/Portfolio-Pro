"""final_notification_type_fix

Revision ID: fbd7836b1d55
Revises: 500578230785
Create Date: 2025-06-11 22:43:04.424970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbd7836b1d55'
down_revision: Union[str, None] = '500578230785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.String(length=20),
        schema='portfolio_pro_app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
