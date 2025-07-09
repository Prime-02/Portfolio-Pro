"""convert_notification_type_to_string

Revision ID: f79ecd8f8e87
Revises: bf8b93d352d8
Create Date: 2025-06-11 22:27:54.888125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f79ecd8f8e87'
down_revision: Union[str, None] = 'bf8b93d352d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # 1. Convert the enum column to string
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.String(length=20),
        postgresql_using='notification_type::text',
        schema='portfolio_pro_app'
    )
    
    # 2. Drop the enum type (only if it exists)
    op.execute('DROP TYPE IF EXISTS portfolio_pro_app.notificationtype')

def downgrade():
    # 1. Recreate the enum type (with your original values)
    op.execute("""
    CREATE TYPE portfolio_pro_app.notificationtype AS ENUM (
        'alert',
        'message',
        'comment'
        -- Add other original enum values here
    );
    """)
    
    # 2. Convert back to enum
    op.alter_column(
        'notifications',
        'notification_type',
        type_=sa.Enum('alert', 'message', 'comment', 
                     name='notificationtype',
                     schema='portfolio_pro_app'),
        postgresql_using='notification_type::portfolio_pro_app.notificationtype',
        schema='portfolio_pro_app'
    )