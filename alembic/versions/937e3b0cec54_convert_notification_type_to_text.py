"""convert_notification_type_to_text

Revision ID: 937e3b0cec54
Revises: 1cedf1b856e5
Create Date: 2025-06-11 21:22:31.745710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '937e3b0cec54'
down_revision: Union[str, None] = '1cedf1b856e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Convert from enum to text
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.String(20),
        postgresql_using='notification_type::text'
    )
    
    # Optional: Drop the enum type if you want to remove it completely
    op.execute("DROP TYPE IF EXISTS notificationtype")

def downgrade():
    # If you might need to revert, recreate the enum
    op.execute("CREATE TYPE notificationtype AS ENUM ('alert', 'message', 'system')")
    
    # Convert back to enum
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.Enum('alert', 'message', 'system', name='notificationtype'),
        postgresql_using='notification_type::notificationtype'
    )
