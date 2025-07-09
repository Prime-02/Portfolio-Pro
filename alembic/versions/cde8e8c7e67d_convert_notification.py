"""convert notification

Revision ID: cde8e8c7e67d
Revises: f79ecd8f8e87
Create Date: 2025-06-11 22:35:07.952024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cde8e8c7e67d'
down_revision: Union[str, None] = 'f79ecd8f8e87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert notification_type from enum to string."""
    # 1. First convert the enum column to string
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.String(length=20),
        postgresql_using='notification_type::text',
        schema='portfolio_pro_app'
    )
    
    # 2. Then drop the enum type
    op.execute('DROP TYPE IF EXISTS portfolio_pro_app.notificationtype')


def downgrade() -> None:
    """Revert notification_type back to enum."""
    # 1. Recreate the original enum type
    op.execute("""
    CREATE TYPE portfolio_pro_app.notificationtype AS ENUM (
        'alert',
        'message',
        'system'
    );
    """)
    
    # 2. Convert the column back to enum type
    op.alter_column(
        'notifications',
        'notification_type',
        type_=postgresql.ENUM(
            'alert', 'message', 'system',
            name='notificationtype',
            schema='portfolio_pro_app'
        ),
        postgresql_using='notification_type::portfolio_pro_app.notificationtype',
        schema='portfolio_pro_app'
    )