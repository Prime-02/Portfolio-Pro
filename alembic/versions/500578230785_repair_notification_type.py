"""repair_notification_type

Revision ID: 500578230785
Revises: cde8e8c7e67d
Create Date: 2025-06-11 22:38:52.339368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '500578230785'
down_revision: Union[str, None] = 'cde8e8c7e67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Check if enum exists first
    conn = op.get_bind()
    enum_exists = conn.execute(
        "SELECT 1 FROM pg_type WHERE typname = 'notificationtype' "
        "AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'portfolio_pro_app')"
    ).scalar()
    
    if not enum_exists:
        # Create the enum type if missing
        op.execute("""
        CREATE TYPE portfolio_pro_app.notificationtype AS ENUM (
            'alert',
            'message',
            'comment'
        );
        """)
    
    # Then convert to string
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.String(length=20),
        postgresql_using='notification_type::text',
        schema='portfolio_pro_app'
    )
    
    # Finally drop the enum
    op.execute('DROP TYPE IF EXISTS portfolio_pro_app.notificationtype')

def downgrade():
    # Recreate enum
    op.execute("""
    CREATE TYPE portfolio_pro_app.notificationtype AS ENUM (
        'alert',
        'message',
        'comment'
    );
    """)
    
    # Convert back to enum
    op.alter_column(
        'notifications',
        'notification_type',
        type_=postgresql.ENUM(
            'alert', 'message', 'comment',
            name='notificationtype',
            schema='portfolio_pro_app'
        ),
        postgresql_using='notification_type::portfolio_pro_app.notificationtype',
        schema='portfolio_pro_app'
    )